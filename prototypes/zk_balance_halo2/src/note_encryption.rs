//! Phase 11: shielded key separation and note encryption.
//!
//! This module deliberately uses RFC 9180 HPKE instead of inventing a new
//! encryption construction. The current research ciphersuite is
//! X25519-HKDF-SHA256 + HKDF-SHA256 + ChaCha20Poly1305.
//!
//! Spend authority, incoming viewing capability, and audit/outgoing viewing
//! capability are separate types. A scanner can be given only an
//! IncomingViewingKey and therefore has no spend-authority material.

use blake2b_simd::Params as Blake2bParams;
use ff::{FromUniformBytes, PrimeField};
use halo2_proofs::pasta::Fp;
use hpke::{
    aead::ChaCha20Poly1305, kdf::HkdfSha256, kem::X25519HkdfSha256, single_shot_open,
    single_shot_seal, Deserializable, Kem as KemTrait, OpModeR, OpModeS, Serializable,
};
use zeroize::Zeroizing;

use crate::{note_action::authority_tag, MAX_WAM_ATOMS};

type Kem = X25519HkdfSha256;
type Aead = ChaCha20Poly1305;
type Kdf = HkdfSha256;
type KemPrivateKey = <Kem as KemTrait>::PrivateKey;
type KemPublicKey = <Kem as KemTrait>::PublicKey;
type KemEncappedKey = <Kem as KemTrait>::EncappedKey;

pub const NOTE_VERSION: u16 = 1;
pub const MAX_MEMO_BYTES: usize = 512;
pub const MAX_CIPHERTEXT_BYTES: usize = 4096;
const HPKE_INFO: &[u8] = b"WAM/Shielded/NoteHPKE/v1";
const NOTE_MAGIC: [u8; 4] = *b"WN11";
const ENCRYPTED_MAGIC: [u8; 4] = *b"WE11";
const AAD_MAGIC: [u8; 4] = *b"WA11";

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NoteCryptoError {
    AmountRange,
    ZeroValue,
    MemoTooLarge,
    AddressMismatch,
    BadPlaintext,
    UnsupportedVersion,
    NonCanonicalField,
    BadPublicKey,
    BadEncappedKey,
    HpkeSeal,
    HpkeOpen,
    Truncated,
    EmptyCiphertext,
    CiphertextTooLarge,
    TrailingBytes,
    RecipientMismatch,
}

fn derive_bytes(seed: &[u8; 32], label: &[u8], len: usize) -> Vec<u8> {
    let mut state = Blake2bParams::new()
        .hash_length(len)
        .personal(b"WAMkey11")
        .to_state();
    state.update(b"WAM/Shielded/KeyHierarchy/v1");
    state.update(label);
    state.update(seed);
    state.finalize().as_bytes().to_vec()
}

fn fp_to_bytes(value: Fp) -> [u8; 32] {
    let repr = value.to_repr();
    let mut out = [0u8; 32];
    out.copy_from_slice(repr.as_ref());
    out
}

fn fp_from_bytes(raw: &[u8]) -> Result<Fp, NoteCryptoError> {
    if raw.len() != 32 {
        return Err(NoteCryptoError::Truncated);
    }
    let mut repr = <Fp as PrimeField>::Repr::default();
    repr.as_mut().copy_from_slice(raw);
    Option::<Fp>::from(Fp::from_repr(repr)).ok_or(NoteCryptoError::NonCanonicalField)
}

fn view_keypair(ikm: &[u8; 32]) -> (KemPrivateKey, KemPublicKey) {
    Kem::derive_keypair(ikm)
}

fn recipient_tag_from_public(public: &KemPublicKey) -> Fp {
    let bytes = public.to_bytes();
    let mut state = Blake2bParams::new()
        .hash_length(64)
        .personal(b"WAMrcp11")
        .to_state();
    state.update(b"WAM/Shielded/RecipientTag/v1");
    state.update(bytes.as_ref());
    let digest = state.finalize();
    let mut wide = [0u8; 64];
    wide.copy_from_slice(digest.as_bytes());
    Fp::from_uniform_bytes(&wide)
}

pub struct SpendAuthority {
    material: Zeroizing<[u8; 64]>,
}

impl SpendAuthority {
    pub fn circuit_secret(&self) -> Fp {
        Fp::from_uniform_bytes(&self.material)
    }

    pub fn public_tag(&self) -> Fp {
        authority_tag(self.circuit_secret())
    }
}

#[derive(Clone)]
pub struct IncomingViewingKey {
    ikm: Zeroizing<[u8; 32]>,
    recipient_tag: Fp,
}

impl IncomingViewingKey {
    pub fn public_key_bytes(&self) -> Vec<u8> {
        let (_, pk) = view_keypair(&self.ikm);
        pk.to_bytes().to_vec()
    }

    pub fn recipient_tag(&self) -> Fp {
        self.recipient_tag
    }

    pub fn decrypt(
        &self,
        encrypted: &EncryptedNote,
        aad: &NoteAad,
    ) -> Result<NotePlaintext, NoteCryptoError> {
        let (sk, _) = view_keypair(&self.ikm);
        let plaintext = open_ciphertext(&sk, &encrypted.recipient, aad)?;
        let note = NotePlaintext::decode(&plaintext)?;
        if note.recipient_tag != self.recipient_tag {
            return Err(NoteCryptoError::RecipientMismatch);
        }
        Ok(note)
    }
}

#[derive(Clone)]
pub struct AuditViewingKey {
    ikm: Zeroizing<[u8; 32]>,
}

impl AuditViewingKey {
    pub fn public_key_bytes(&self) -> Vec<u8> {
        let (_, pk) = view_keypair(&self.ikm);
        pk.to_bytes().to_vec()
    }

    pub fn decrypt(
        &self,
        encrypted: &EncryptedNote,
        aad: &NoteAad,
    ) -> Result<NotePlaintext, NoteCryptoError> {
        let (sk, _) = view_keypair(&self.ikm);
        let plaintext = open_ciphertext(&sk, &encrypted.audit, aad)?;
        NotePlaintext::decode(&plaintext)
    }
}

pub struct ShieldedKeyBundle {
    spend: SpendAuthority,
    incoming: IncomingViewingKey,
    audit: AuditViewingKey,
}

impl ShieldedKeyBundle {
    pub fn derive(seed: [u8; 32]) -> Self {
        let seed = Zeroizing::new(seed);
        let spend_vec = Zeroizing::new(derive_bytes(&seed, b"spend-authority", 64));
        let incoming_vec = Zeroizing::new(derive_bytes(&seed, b"incoming-view", 32));
        let audit_vec = Zeroizing::new(derive_bytes(&seed, b"audit-view", 32));

        let mut spend = [0u8; 64];
        spend.copy_from_slice(&spend_vec);
        let mut incoming = [0u8; 32];
        incoming.copy_from_slice(&incoming_vec);
        let mut audit = [0u8; 32];
        audit.copy_from_slice(&audit_vec);

        let (_, incoming_public) = view_keypair(&incoming);
        let recipient_tag = recipient_tag_from_public(&incoming_public);

        Self {
            spend: SpendAuthority {
                material: Zeroizing::new(spend),
            },
            incoming: IncomingViewingKey {
                ikm: Zeroizing::new(incoming),
                recipient_tag,
            },
            audit: AuditViewingKey {
                ikm: Zeroizing::new(audit),
            },
        }
    }

    pub fn spend_authority(&self) -> &SpendAuthority {
        &self.spend
    }

    pub fn incoming_viewing_key(&self) -> IncomingViewingKey {
        self.incoming.clone()
    }

    pub fn audit_viewing_key(&self) -> AuditViewingKey {
        self.audit.clone()
    }

    pub fn address(&self) -> ShieldedAddress {
        ShieldedAddress {
            incoming_view_public: self.incoming.public_key_bytes(),
            audit_public: self.audit.public_key_bytes(),
            recipient_tag: self.incoming.recipient_tag(),
            spend_authority_tag: self.spend.public_tag(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ShieldedAddress {
    pub incoming_view_public: Vec<u8>,
    pub audit_public: Vec<u8>,
    pub recipient_tag: Fp,
    pub spend_authority_tag: Fp,
}

#[derive(Clone, PartialEq, Eq)]
pub struct NotePlaintext {
    pub value: u64,
    pub recipient_tag: Fp,
    pub spend_authority_tag: Fp,
    pub rho: Fp,
    pub rseed: Fp,
    pub memo: Vec<u8>,
}

impl std::fmt::Debug for NotePlaintext {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("NotePlaintext(<redacted>)")
    }
}

impl NotePlaintext {
    pub fn validate(&self) -> Result<(), NoteCryptoError> {
        if self.value == 0 {
            return Err(NoteCryptoError::ZeroValue);
        }
        if self.value > MAX_WAM_ATOMS {
            return Err(NoteCryptoError::AmountRange);
        }
        if self.memo.len() > MAX_MEMO_BYTES {
            return Err(NoteCryptoError::MemoTooLarge);
        }
        Ok(())
    }

    pub fn encode(&self) -> Result<Vec<u8>, NoteCryptoError> {
        self.validate()?;
        let memo_len = u16::try_from(self.memo.len()).map_err(|_| NoteCryptoError::MemoTooLarge)?;
        let mut out = Vec::with_capacity(4 + 2 + 8 + 4 * 32 + 2 + self.memo.len());
        out.extend_from_slice(&NOTE_MAGIC);
        out.extend_from_slice(&NOTE_VERSION.to_le_bytes());
        out.extend_from_slice(&self.value.to_le_bytes());
        for field in [
            self.recipient_tag,
            self.spend_authority_tag,
            self.rho,
            self.rseed,
        ] {
            out.extend_from_slice(&fp_to_bytes(field));
        }
        out.extend_from_slice(&memo_len.to_le_bytes());
        out.extend_from_slice(&self.memo);
        Ok(out)
    }

    pub fn decode(encoded: &[u8]) -> Result<Self, NoteCryptoError> {
        let mut cursor = 0usize;
        if take(encoded, &mut cursor, 4)? != NOTE_MAGIC {
            return Err(NoteCryptoError::BadPlaintext);
        }
        let version = u16::from_le_bytes(
            take(encoded, &mut cursor, 2)?
                .try_into()
                .map_err(|_| NoteCryptoError::Truncated)?,
        );
        if version != NOTE_VERSION {
            return Err(NoteCryptoError::UnsupportedVersion);
        }
        let value = u64::from_le_bytes(
            take(encoded, &mut cursor, 8)?
                .try_into()
                .map_err(|_| NoteCryptoError::Truncated)?,
        );
        let recipient_tag = fp_from_bytes(take(encoded, &mut cursor, 32)?)?;
        let spend_authority_tag = fp_from_bytes(take(encoded, &mut cursor, 32)?)?;
        let rho = fp_from_bytes(take(encoded, &mut cursor, 32)?)?;
        let rseed = fp_from_bytes(take(encoded, &mut cursor, 32)?)?;
        let memo_len = u16::from_le_bytes(
            take(encoded, &mut cursor, 2)?
                .try_into()
                .map_err(|_| NoteCryptoError::Truncated)?,
        ) as usize;
        if memo_len > MAX_MEMO_BYTES {
            return Err(NoteCryptoError::MemoTooLarge);
        }
        let memo = take(encoded, &mut cursor, memo_len)?.to_vec();
        if cursor != encoded.len() {
            return Err(NoteCryptoError::TrailingBytes);
        }
        let note = Self {
            value,
            recipient_tag,
            spend_authority_tag,
            rho,
            rseed,
            memo,
        };
        note.validate()?;
        Ok(note)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NoteAad {
    pub network_id: u32,
    pub transaction_digest: [u8; 32],
    pub output_index: u32,
    pub note_commitment: [u8; 32],
    pub context_digest: [u8; 32],
}

impl NoteAad {
    pub fn encode(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(4 + 2 + 4 + 32 + 4 + 32 + 32);
        out.extend_from_slice(&AAD_MAGIC);
        out.extend_from_slice(&NOTE_VERSION.to_le_bytes());
        out.extend_from_slice(&self.network_id.to_le_bytes());
        out.extend_from_slice(&self.transaction_digest);
        out.extend_from_slice(&self.output_index.to_le_bytes());
        out.extend_from_slice(&self.note_commitment);
        out.extend_from_slice(&self.context_digest);
        out
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NoteCiphertext {
    pub encapped_key: Vec<u8>,
    pub ciphertext: Vec<u8>,
}

impl NoteCiphertext {
    fn validate(&self) -> Result<(), NoteCryptoError> {
        if self.encapped_key.is_empty() || self.ciphertext.is_empty() {
            return Err(NoteCryptoError::EmptyCiphertext);
        }
        if self.encapped_key.len() > 256 || self.ciphertext.len() > MAX_CIPHERTEXT_BYTES {
            return Err(NoteCryptoError::CiphertextTooLarge);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EncryptedNote {
    pub recipient: NoteCiphertext,
    pub audit: NoteCiphertext,
}

impl EncryptedNote {
    pub fn encode(&self) -> Result<Vec<u8>, NoteCryptoError> {
        self.recipient.validate()?;
        self.audit.validate()?;
        let mut out = Vec::new();
        out.extend_from_slice(&ENCRYPTED_MAGIC);
        out.extend_from_slice(&NOTE_VERSION.to_le_bytes());
        encode_ciphertext(&mut out, &self.recipient)?;
        encode_ciphertext(&mut out, &self.audit)?;
        Ok(out)
    }

    pub fn decode(encoded: &[u8]) -> Result<Self, NoteCryptoError> {
        let mut cursor = 0usize;
        if take(encoded, &mut cursor, 4)? != ENCRYPTED_MAGIC {
            return Err(NoteCryptoError::BadPlaintext);
        }
        let version = u16::from_le_bytes(
            take(encoded, &mut cursor, 2)?
                .try_into()
                .map_err(|_| NoteCryptoError::Truncated)?,
        );
        if version != NOTE_VERSION {
            return Err(NoteCryptoError::UnsupportedVersion);
        }
        let recipient = decode_ciphertext(encoded, &mut cursor)?;
        let audit = decode_ciphertext(encoded, &mut cursor)?;
        if cursor != encoded.len() {
            return Err(NoteCryptoError::TrailingBytes);
        }
        Ok(Self { recipient, audit })
    }
}

pub fn encrypt_note(
    address: &ShieldedAddress,
    note: &NotePlaintext,
    aad: &NoteAad,
) -> Result<EncryptedNote, NoteCryptoError> {
    note.validate()?;
    if note.recipient_tag != address.recipient_tag
        || note.spend_authority_tag != address.spend_authority_tag
    {
        return Err(NoteCryptoError::AddressMismatch);
    }
    let plaintext = note.encode()?;
    Ok(EncryptedNote {
        recipient: seal_to(&address.incoming_view_public, &plaintext, aad)?,
        audit: seal_to(&address.audit_public, &plaintext, aad)?,
    })
}

fn seal_to(
    public_bytes: &[u8],
    plaintext: &[u8],
    aad: &NoteAad,
) -> Result<NoteCiphertext, NoteCryptoError> {
    let public =
        KemPublicKey::from_bytes(public_bytes).map_err(|_| NoteCryptoError::BadPublicKey)?;
    let (encapped, ciphertext) = single_shot_seal::<Aead, Kdf, Kem>(
        &OpModeS::Base,
        &public,
        HPKE_INFO,
        plaintext,
        &aad.encode(),
    )
    .map_err(|_| NoteCryptoError::HpkeSeal)?;
    Ok(NoteCiphertext {
        encapped_key: encapped.to_bytes().to_vec(),
        ciphertext,
    })
}

fn open_ciphertext(
    secret: &KemPrivateKey,
    ciphertext: &NoteCiphertext,
    aad: &NoteAad,
) -> Result<Vec<u8>, NoteCryptoError> {
    ciphertext.validate()?;
    let encapped = KemEncappedKey::from_bytes(&ciphertext.encapped_key)
        .map_err(|_| NoteCryptoError::BadEncappedKey)?;
    single_shot_open::<Aead, Kdf, Kem>(
        &OpModeR::Base,
        secret,
        &encapped,
        HPKE_INFO,
        &ciphertext.ciphertext,
        &aad.encode(),
    )
    .map_err(|_| NoteCryptoError::HpkeOpen)
}

fn encode_ciphertext(out: &mut Vec<u8>, value: &NoteCiphertext) -> Result<(), NoteCryptoError> {
    value.validate()?;
    let enc_len =
        u16::try_from(value.encapped_key.len()).map_err(|_| NoteCryptoError::CiphertextTooLarge)?;
    let ct_len =
        u32::try_from(value.ciphertext.len()).map_err(|_| NoteCryptoError::CiphertextTooLarge)?;
    out.extend_from_slice(&enc_len.to_le_bytes());
    out.extend_from_slice(&ct_len.to_le_bytes());
    out.extend_from_slice(&value.encapped_key);
    out.extend_from_slice(&value.ciphertext);
    Ok(())
}

fn decode_ciphertext(
    encoded: &[u8],
    cursor: &mut usize,
) -> Result<NoteCiphertext, NoteCryptoError> {
    let enc_len = u16::from_le_bytes(
        take(encoded, cursor, 2)?
            .try_into()
            .map_err(|_| NoteCryptoError::Truncated)?,
    ) as usize;
    let ct_len = u32::from_le_bytes(
        take(encoded, cursor, 4)?
            .try_into()
            .map_err(|_| NoteCryptoError::Truncated)?,
    ) as usize;
    if enc_len == 0 || ct_len == 0 {
        return Err(NoteCryptoError::EmptyCiphertext);
    }
    if enc_len > 256 || ct_len > MAX_CIPHERTEXT_BYTES {
        return Err(NoteCryptoError::CiphertextTooLarge);
    }
    let value = NoteCiphertext {
        encapped_key: take(encoded, cursor, enc_len)?.to_vec(),
        ciphertext: take(encoded, cursor, ct_len)?.to_vec(),
    };
    value.validate()?;
    Ok(value)
}

fn take<'a>(
    encoded: &'a [u8],
    cursor: &mut usize,
    len: usize,
) -> Result<&'a [u8], NoteCryptoError> {
    let end = cursor.checked_add(len).ok_or(NoteCryptoError::Truncated)?;
    if end > encoded.len() {
        return Err(NoteCryptoError::Truncated);
    }
    let out = &encoded[*cursor..end];
    *cursor = end;
    Ok(out)
}
