//! Phase 10D: context-bound canonical envelope for the hardened 2x2 bundle.
//!
//! This supersedes the Phase 10C research envelope for the hardened profile.
//! The verifier derives the VK identifier from the pinned verification key and
//! requires the proof's public context digest to match the expected WAM
//! protocol/network/transaction context.

use blake2b_simd::Params as Blake2bParams;
use ff::PrimeField;
use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{verify_proof, SingleVerifier, VerifyingKey},
    poly::commitment::Params,
    transcript::{Blake2bRead, Challenge255},
};

use crate::context::{ProofContext, CIRCUIT_ID_HARDENED_2X2};

pub const MAGIC: [u8; 4] = *b"W10D";
pub const FORMAT_VERSION: u16 = 2;
pub const PUBLIC_INPUT_COUNT: usize = 9;
pub const VK_ID_BYTES: usize = 32;
pub const MAX_PROOF_BYTES: usize = 4 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum HardenedEnvelopeError {
    Truncated,
    BadMagic,
    UnsupportedVersion,
    UnsupportedCircuit,
    WrongInstanceCount,
    NonCanonicalField,
    EmptyProof,
    ProofTooLarge,
    TrailingBytes,
    VkIdMismatch,
    ContextMismatch,
    TransparentBalanceMismatch,
    ProofRejected,
}

#[derive(Clone, Debug)]
pub struct HardenedBundleEnvelope {
    pub vk_id: [u8; VK_ID_BYTES],
    pub public_inputs: [Fp; PUBLIC_INPUT_COUNT],
    pub proof: Vec<u8>,
}

pub fn vk_identifier(vk: &VerifyingKey<EqAffine>) -> [u8; VK_ID_BYTES] {
    // halo2_proofs::VerifyingKey::pinned() is the library's minimal active
    // representation of a VK. The dependency version is pinned by Cargo.lock;
    // the domain string prevents cross-protocol reuse of this identifier.
    let pinned = format!("{:#?}", vk.pinned());
    let digest = Blake2bParams::new()
        .hash_length(VK_ID_BYTES)
        .personal(b"WAMvk10d")
        .hash(pinned.as_bytes());
    let mut out = [0u8; VK_ID_BYTES];
    out.copy_from_slice(digest.as_bytes());
    out
}

impl HardenedBundleEnvelope {
    pub fn new(
        vk: &VerifyingKey<EqAffine>,
        public_inputs: [Fp; PUBLIC_INPUT_COUNT],
        proof: Vec<u8>,
    ) -> Result<Self, HardenedEnvelopeError> {
        if proof.is_empty() {
            return Err(HardenedEnvelopeError::EmptyProof);
        }
        if proof.len() > MAX_PROOF_BYTES {
            return Err(HardenedEnvelopeError::ProofTooLarge);
        }
        Ok(Self {
            vk_id: vk_identifier(vk),
            public_inputs,
            proof,
        })
    }

    pub fn encode(&self) -> Result<Vec<u8>, HardenedEnvelopeError> {
        if self.proof.is_empty() {
            return Err(HardenedEnvelopeError::EmptyProof);
        }
        if self.proof.len() > MAX_PROOF_BYTES {
            return Err(HardenedEnvelopeError::ProofTooLarge);
        }
        let proof_len =
            u32::try_from(self.proof.len()).map_err(|_| HardenedEnvelopeError::ProofTooLarge)?;
        let mut out = Vec::with_capacity(
            MAGIC.len() + 2 + 2 + VK_ID_BYTES + 1 + PUBLIC_INPUT_COUNT * 32 + 4 + self.proof.len(),
        );
        out.extend_from_slice(&MAGIC);
        out.extend_from_slice(&FORMAT_VERSION.to_le_bytes());
        out.extend_from_slice(&CIRCUIT_ID_HARDENED_2X2.to_le_bytes());
        out.extend_from_slice(&self.vk_id);
        out.push(PUBLIC_INPUT_COUNT as u8);
        for value in &self.public_inputs {
            out.extend_from_slice(value.to_repr().as_ref());
        }
        out.extend_from_slice(&proof_len.to_le_bytes());
        out.extend_from_slice(&self.proof);
        Ok(out)
    }

    pub fn decode(encoded: &[u8]) -> Result<Self, HardenedEnvelopeError> {
        let mut cursor = 0usize;
        if take(encoded, &mut cursor, 4)? != MAGIC {
            return Err(HardenedEnvelopeError::BadMagic);
        }
        let version = u16::from_le_bytes(
            take(encoded, &mut cursor, 2)?
                .try_into()
                .map_err(|_| HardenedEnvelopeError::Truncated)?,
        );
        if version != FORMAT_VERSION {
            return Err(HardenedEnvelopeError::UnsupportedVersion);
        }
        let circuit_id = u16::from_le_bytes(
            take(encoded, &mut cursor, 2)?
                .try_into()
                .map_err(|_| HardenedEnvelopeError::Truncated)?,
        );
        if circuit_id != CIRCUIT_ID_HARDENED_2X2 {
            return Err(HardenedEnvelopeError::UnsupportedCircuit);
        }

        let mut vk_id = [0u8; VK_ID_BYTES];
        vk_id.copy_from_slice(take(encoded, &mut cursor, VK_ID_BYTES)?);

        let count = *take(encoded, &mut cursor, 1)?
            .first()
            .ok_or(HardenedEnvelopeError::Truncated)? as usize;
        if count != PUBLIC_INPUT_COUNT {
            return Err(HardenedEnvelopeError::WrongInstanceCount);
        }

        let mut values = Vec::with_capacity(PUBLIC_INPUT_COUNT);
        for _ in 0..PUBLIC_INPUT_COUNT {
            let raw = take(encoded, &mut cursor, 32)?;
            let mut repr = <Fp as PrimeField>::Repr::default();
            repr.as_mut().copy_from_slice(raw);
            let value = Option::<Fp>::from(Fp::from_repr(repr))
                .ok_or(HardenedEnvelopeError::NonCanonicalField)?;
            values.push(value);
        }

        let proof_len = u32::from_le_bytes(
            take(encoded, &mut cursor, 4)?
                .try_into()
                .map_err(|_| HardenedEnvelopeError::Truncated)?,
        ) as usize;
        if proof_len == 0 {
            return Err(HardenedEnvelopeError::EmptyProof);
        }
        if proof_len > MAX_PROOF_BYTES {
            return Err(HardenedEnvelopeError::ProofTooLarge);
        }
        let proof = take(encoded, &mut cursor, proof_len)?.to_vec();
        if cursor != encoded.len() {
            return Err(HardenedEnvelopeError::TrailingBytes);
        }

        Ok(Self {
            vk_id,
            public_inputs: values
                .try_into()
                .map_err(|_| HardenedEnvelopeError::WrongInstanceCount)?,
            proof,
        })
    }
}

pub fn verify_hardened_bundle_envelope(
    params: &Params<EqAffine>,
    vk: &VerifyingKey<EqAffine>,
    expected_context: &ProofContext,
    encoded: &[u8],
) -> Result<(), HardenedEnvelopeError> {
    let envelope = HardenedBundleEnvelope::decode(encoded)?;
    if envelope.vk_id != vk_identifier(vk) {
        return Err(HardenedEnvelopeError::VkIdMismatch);
    }
    if envelope.public_inputs[8] != expected_context.digest() {
        return Err(HardenedEnvelopeError::ContextMismatch);
    }
    if envelope.public_inputs[5] != Fp::from(expected_context.fee)
        || envelope.public_inputs[6] != Fp::from(expected_context.transparent_in)
        || envelope.public_inputs[7] != Fp::from(expected_context.transparent_out)
    {
        return Err(HardenedEnvelopeError::TransparentBalanceMismatch);
    }

    let instance_columns: &[&[Fp]] = &[&envelope.public_inputs];
    let strategy = SingleVerifier::new(params);
    let mut transcript =
        Blake2bRead::<_, EqAffine, Challenge255<_>>::init(envelope.proof.as_slice());

    verify_proof(params, vk, strategy, &[instance_columns], &mut transcript)
        .map_err(|_| HardenedEnvelopeError::ProofRejected)
}

fn take<'a>(
    encoded: &'a [u8],
    cursor: &mut usize,
    len: usize,
) -> Result<&'a [u8], HardenedEnvelopeError> {
    let end = cursor
        .checked_add(len)
        .ok_or(HardenedEnvelopeError::Truncated)?;
    if end > encoded.len() {
        return Err(HardenedEnvelopeError::Truncated);
    }
    let out = &encoded[*cursor..end];
    *cursor = end;
    Ok(out)
}
