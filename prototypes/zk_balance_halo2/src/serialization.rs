//! Phase 10C: canonical research envelope and verifier contract for Phase 10B.
//!
//! This is deliberately a research serialization. It does not define WAM
//! consensus bytes or a production transaction format.

use ff::PrimeField;
use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{verify_proof, SingleVerifier, VerifyingKey},
    poly::commitment::Params,
    transcript::{Blake2bRead, Challenge255},
};

pub const MAGIC: [u8; 4] = *b"W10C";
pub const FORMAT_VERSION: u16 = 1;
pub const CIRCUIT_ID_FIXED_2X2: u16 = 0x0A02;
pub const PUBLIC_INPUT_COUNT: usize = 8;
pub const VK_ID_BYTES: usize = 32;
pub const MAX_PROOF_BYTES: usize = 4 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EnvelopeError {
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
    ProofRejected,
}

#[derive(Clone, Debug)]
pub struct BundleProofEnvelope {
    pub vk_id: [u8; VK_ID_BYTES],
    pub public_inputs: [Fp; PUBLIC_INPUT_COUNT],
    pub proof: Vec<u8>,
}

impl BundleProofEnvelope {
    pub fn new(
        vk_id: [u8; VK_ID_BYTES],
        public_inputs: [Fp; PUBLIC_INPUT_COUNT],
        proof: Vec<u8>,
    ) -> Result<Self, EnvelopeError> {
        if proof.is_empty() {
            return Err(EnvelopeError::EmptyProof);
        }
        if proof.len() > MAX_PROOF_BYTES {
            return Err(EnvelopeError::ProofTooLarge);
        }
        Ok(Self {
            vk_id,
            public_inputs,
            proof,
        })
    }

    pub fn encode(&self) -> Result<Vec<u8>, EnvelopeError> {
        if self.proof.is_empty() {
            return Err(EnvelopeError::EmptyProof);
        }
        if self.proof.len() > MAX_PROOF_BYTES {
            return Err(EnvelopeError::ProofTooLarge);
        }

        let proof_len =
            u32::try_from(self.proof.len()).map_err(|_| EnvelopeError::ProofTooLarge)?;
        let mut out = Vec::with_capacity(
            MAGIC.len() + 2 + 2 + VK_ID_BYTES + 1 + PUBLIC_INPUT_COUNT * 32 + 4 + self.proof.len(),
        );
        out.extend_from_slice(&MAGIC);
        out.extend_from_slice(&FORMAT_VERSION.to_le_bytes());
        out.extend_from_slice(&CIRCUIT_ID_FIXED_2X2.to_le_bytes());
        out.extend_from_slice(&self.vk_id);
        out.push(PUBLIC_INPUT_COUNT as u8);

        for value in &self.public_inputs {
            out.extend_from_slice(value.to_repr().as_ref());
        }

        out.extend_from_slice(&proof_len.to_le_bytes());
        out.extend_from_slice(&self.proof);
        Ok(out)
    }

    pub fn decode(encoded: &[u8]) -> Result<Self, EnvelopeError> {
        let mut cursor = 0usize;

        let magic = take(encoded, &mut cursor, 4)?;
        if magic != MAGIC {
            return Err(EnvelopeError::BadMagic);
        }

        let version = u16::from_le_bytes(
            take(encoded, &mut cursor, 2)?
                .try_into()
                .map_err(|_| EnvelopeError::Truncated)?,
        );
        if version != FORMAT_VERSION {
            return Err(EnvelopeError::UnsupportedVersion);
        }

        let circuit_id = u16::from_le_bytes(
            take(encoded, &mut cursor, 2)?
                .try_into()
                .map_err(|_| EnvelopeError::Truncated)?,
        );
        if circuit_id != CIRCUIT_ID_FIXED_2X2 {
            return Err(EnvelopeError::UnsupportedCircuit);
        }

        let mut vk_id = [0u8; VK_ID_BYTES];
        vk_id.copy_from_slice(take(encoded, &mut cursor, VK_ID_BYTES)?);

        let instance_count = *take(encoded, &mut cursor, 1)?
            .first()
            .ok_or(EnvelopeError::Truncated)? as usize;
        if instance_count != PUBLIC_INPUT_COUNT {
            return Err(EnvelopeError::WrongInstanceCount);
        }

        let mut public = Vec::with_capacity(PUBLIC_INPUT_COUNT);
        for _ in 0..PUBLIC_INPUT_COUNT {
            let raw = take(encoded, &mut cursor, 32)?;
            let mut repr = <Fp as PrimeField>::Repr::default();
            repr.as_mut().copy_from_slice(raw);
            let value =
                Option::<Fp>::from(Fp::from_repr(repr)).ok_or(EnvelopeError::NonCanonicalField)?;
            public.push(value);
        }

        let proof_len = u32::from_le_bytes(
            take(encoded, &mut cursor, 4)?
                .try_into()
                .map_err(|_| EnvelopeError::Truncated)?,
        ) as usize;
        if proof_len == 0 {
            return Err(EnvelopeError::EmptyProof);
        }
        if proof_len > MAX_PROOF_BYTES {
            return Err(EnvelopeError::ProofTooLarge);
        }

        let proof = take(encoded, &mut cursor, proof_len)?.to_vec();
        if cursor != encoded.len() {
            return Err(EnvelopeError::TrailingBytes);
        }

        let public_inputs: [Fp; PUBLIC_INPUT_COUNT] = public
            .try_into()
            .map_err(|_| EnvelopeError::WrongInstanceCount)?;

        Ok(Self {
            vk_id,
            public_inputs,
            proof,
        })
    }
}

pub fn verify_bundle_envelope(
    params: &Params<EqAffine>,
    vk: &VerifyingKey<EqAffine>,
    expected_vk_id: [u8; VK_ID_BYTES],
    encoded: &[u8],
) -> Result<(), EnvelopeError> {
    let envelope = BundleProofEnvelope::decode(encoded)?;
    if envelope.vk_id != expected_vk_id {
        return Err(EnvelopeError::VkIdMismatch);
    }

    let instance_columns: &[&[Fp]] = &[&envelope.public_inputs];
    let strategy = SingleVerifier::new(params);
    let mut transcript =
        Blake2bRead::<_, EqAffine, Challenge255<_>>::init(envelope.proof.as_slice());

    verify_proof(params, vk, strategy, &[instance_columns], &mut transcript)
        .map_err(|_| EnvelopeError::ProofRejected)
}

fn take<'a>(encoded: &'a [u8], cursor: &mut usize, len: usize) -> Result<&'a [u8], EnvelopeError> {
    let end = cursor.checked_add(len).ok_or(EnvelopeError::Truncated)?;
    if end > encoded.len() {
        return Err(EnvelopeError::Truncated);
    }
    let out = &encoded[*cursor..end];
    *cursor = end;
    Ok(out)
}
