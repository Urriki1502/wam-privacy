use halo2_proofs::pasta::Fp;
use wam_privacy_halo2_prototype::{
    note_encryption::{
        encrypt_note, EncryptedNote, NoteAad, NoteCryptoError, NotePlaintext, ShieldedKeyBundle,
        MAX_MEMO_BYTES,
    },
    MAX_WAM_ATOMS,
};

fn aad() -> NoteAad {
    NoteAad {
        network_id: 3,
        transaction_digest: [0x11; 32],
        output_index: 7,
        note_commitment: [0x22; 32],
        context_digest: [0x33; 32],
    }
}

fn fixture() -> (ShieldedKeyBundle, NotePlaintext) {
    let keys = ShieldedKeyBundle::derive([0x42; 32]);
    let address = keys.address();
    let note = NotePlaintext {
        value: 123_456,
        recipient_tag: address.recipient_tag,
        spend_authority_tag: address.spend_authority_tag,
        rho: Fp::from(0x4444),
        rseed: Fp::from(0x5555),
        memo: b"phase-11-private-memo".to_vec(),
    };
    (keys, note)
}

#[test]
fn deterministic_recovery_recreates_the_same_public_address() {
    let a = ShieldedKeyBundle::derive([0x42; 32]).address();
    let b = ShieldedKeyBundle::derive([0x42; 32]).address();
    let c = ShieldedKeyBundle::derive([0x43; 32]).address();

    assert_eq!(a, b);
    assert_ne!(a, c);
    assert_ne!(a.incoming_view_public, a.audit_public);
    assert_ne!(a.recipient_tag, a.spend_authority_tag);
}

#[test]
fn incoming_and_audit_capabilities_decrypt_without_spend_material() {
    let (keys, note) = fixture();
    let address = keys.address();
    let encrypted = encrypt_note(&address, &note, &aad()).expect("encrypt");

    let incoming = keys.incoming_viewing_key();
    let audit = keys.audit_viewing_key();

    assert_eq!(
        incoming
            .decrypt(&encrypted, &aad())
            .expect("incoming decrypt"),
        note
    );
    assert_eq!(
        audit.decrypt(&encrypted, &aad()).expect("audit decrypt"),
        note
    );
    assert_eq!(incoming.recipient_tag(), address.recipient_tag);
    assert_eq!(
        keys.spend_authority().public_tag(),
        address.spend_authority_tag
    );
}

#[test]
fn wrong_viewing_key_and_cross_role_ciphertext_fail_closed() {
    let (keys, note) = fixture();
    let encrypted = encrypt_note(&keys.address(), &note, &aad()).expect("encrypt");
    let wrong = ShieldedKeyBundle::derive([0x99; 32]);

    assert_eq!(
        wrong
            .incoming_viewing_key()
            .decrypt(&encrypted, &aad())
            .unwrap_err(),
        NoteCryptoError::HpkeOpen
    );
    assert_eq!(
        wrong
            .audit_viewing_key()
            .decrypt(&encrypted, &aad())
            .unwrap_err(),
        NoteCryptoError::HpkeOpen
    );

    let cross = EncryptedNote {
        recipient: encrypted.audit.clone(),
        audit: encrypted.recipient.clone(),
    };
    assert_eq!(
        keys.incoming_viewing_key()
            .decrypt(&cross, &aad())
            .unwrap_err(),
        NoteCryptoError::HpkeOpen
    );
}

#[test]
fn associated_data_tampering_is_rejected() {
    let (keys, note) = fixture();
    let encrypted = encrypt_note(&keys.address(), &note, &aad()).expect("encrypt");

    let mut changed = aad();
    changed.transaction_digest[0] ^= 1;
    assert_eq!(
        keys.incoming_viewing_key()
            .decrypt(&encrypted, &changed)
            .unwrap_err(),
        NoteCryptoError::HpkeOpen
    );

    let mut changed = aad();
    changed.output_index += 1;
    assert_eq!(
        keys.incoming_viewing_key()
            .decrypt(&encrypted, &changed)
            .unwrap_err(),
        NoteCryptoError::HpkeOpen
    );

    let mut changed = aad();
    changed.note_commitment[0] ^= 1;
    assert_eq!(
        keys.audit_viewing_key()
            .decrypt(&encrypted, &changed)
            .unwrap_err(),
        NoteCryptoError::HpkeOpen
    );
}

#[test]
fn encryption_is_randomized_but_roundtrips_canonically() {
    let (keys, note) = fixture();
    let first = encrypt_note(&keys.address(), &note, &aad()).expect("encrypt 1");
    let second = encrypt_note(&keys.address(), &note, &aad()).expect("encrypt 2");

    assert_ne!(first.recipient.encapped_key, second.recipient.encapped_key);
    assert_ne!(first.recipient.ciphertext, second.recipient.ciphertext);

    let encoded = first.encode().expect("encode");
    let decoded = EncryptedNote::decode(&encoded).expect("decode");
    assert_eq!(decoded, first);
    assert_eq!(decoded.encode().expect("reencode"), encoded);
}

#[test]
fn plaintext_and_encrypted_formats_fail_closed() {
    let (keys, note) = fixture();
    let encoded = note.encode().expect("note encode");

    let mut wrong_version = encoded.clone();
    wrong_version[4..6].copy_from_slice(&2u16.to_le_bytes());
    assert_eq!(
        NotePlaintext::decode(&wrong_version).unwrap_err(),
        NoteCryptoError::UnsupportedVersion
    );

    let mut noncanonical = encoded.clone();
    noncanonical[14..46].fill(0xff);
    assert_eq!(
        NotePlaintext::decode(&noncanonical).unwrap_err(),
        NoteCryptoError::NonCanonicalField
    );

    let mut trailing = encoded;
    trailing.push(0);
    assert_eq!(
        NotePlaintext::decode(&trailing).unwrap_err(),
        NoteCryptoError::TrailingBytes
    );

    let encrypted = encrypt_note(&keys.address(), &note, &aad()).expect("encrypt");
    let encoded = encrypted.encode().expect("encrypted encode");
    assert_eq!(
        EncryptedNote::decode(&encoded[..encoded.len() - 1]).unwrap_err(),
        NoteCryptoError::Truncated
    );
    let mut trailing = encoded;
    trailing.push(0);
    assert_eq!(
        EncryptedNote::decode(&trailing).unwrap_err(),
        NoteCryptoError::TrailingBytes
    );
}

#[test]
fn amount_memo_and_address_mismatch_rules_are_enforced() {
    let (keys, mut note) = fixture();

    note.value = 0;
    assert_eq!(note.encode().unwrap_err(), NoteCryptoError::ZeroValue);

    let (_, mut note) = fixture();
    note.value = MAX_WAM_ATOMS + 1;
    assert_eq!(note.encode().unwrap_err(), NoteCryptoError::AmountRange);

    let (_, mut note) = fixture();
    note.memo = vec![0; MAX_MEMO_BYTES + 1];
    assert_eq!(note.encode().unwrap_err(), NoteCryptoError::MemoTooLarge);

    let (_, mut note) = fixture();
    note.recipient_tag += Fp::from(1);
    assert_eq!(
        encrypt_note(&keys.address(), &note, &aad()).unwrap_err(),
        NoteCryptoError::AddressMismatch
    );
}

#[test]
fn private_note_debug_never_prints_value_keys_or_memo() {
    let (_keys, note) = fixture();
    let debug = format!("{note:?}");
    assert_eq!(debug, "NotePlaintext(<redacted>)");
    assert!(!debug.contains("phase-11-private-memo"));
    assert!(!debug.contains("123456"));
}
