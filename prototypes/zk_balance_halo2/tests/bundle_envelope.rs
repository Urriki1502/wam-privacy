use halo2_proofs::pasta::Fp;
use wam_privacy_halo2_prototype::serialization::{
    BundleProofEnvelope, EnvelopeError, CIRCUIT_ID_FIXED_2X2, FORMAT_VERSION, MAGIC,
    MAX_PROOF_BYTES, PUBLIC_INPUT_COUNT,
};

fn fixture() -> BundleProofEnvelope {
    let public_inputs: [Fp; PUBLIC_INPUT_COUNT] =
        core::array::from_fn(|index| Fp::from((index as u64) + 1));
    BundleProofEnvelope::new([0xA5; 32], public_inputs, vec![1, 2, 3, 4])
        .expect("fixture envelope")
}

#[test]
fn canonical_roundtrip_is_deterministic() {
    let envelope = fixture();
    let encoded = envelope.encode().expect("encode");
    let decoded = BundleProofEnvelope::decode(&encoded).expect("decode");

    assert_eq!(decoded.vk_id, envelope.vk_id);
    assert_eq!(decoded.public_inputs, envelope.public_inputs);
    assert_eq!(decoded.proof, envelope.proof);
    assert_eq!(decoded.encode().expect("re-encode"), encoded);
}

#[test]
fn header_is_explicit_and_versioned() {
    let encoded = fixture().encode().expect("encode");
    assert_eq!(&encoded[0..4], &MAGIC);
    assert_eq!(
        u16::from_le_bytes(encoded[4..6].try_into().unwrap()),
        FORMAT_VERSION
    );
    assert_eq!(
        u16::from_le_bytes(encoded[6..8].try_into().unwrap()),
        CIRCUIT_ID_FIXED_2X2
    );
    assert_eq!(encoded[40] as usize, PUBLIC_INPUT_COUNT);
}

#[test]
fn malformed_headers_fail_closed() {
    let encoded = fixture().encode().expect("encode");

    let mut bad = encoded.clone();
    bad[0] ^= 1;
    assert_eq!(
        BundleProofEnvelope::decode(&bad).unwrap_err(),
        EnvelopeError::BadMagic
    );

    let mut bad = encoded.clone();
    bad[4..6].copy_from_slice(&(FORMAT_VERSION + 1).to_le_bytes());
    assert_eq!(
        BundleProofEnvelope::decode(&bad).unwrap_err(),
        EnvelopeError::UnsupportedVersion
    );

    let mut bad = encoded.clone();
    bad[6..8].copy_from_slice(&(CIRCUIT_ID_FIXED_2X2 + 1).to_le_bytes());
    assert_eq!(
        BundleProofEnvelope::decode(&bad).unwrap_err(),
        EnvelopeError::UnsupportedCircuit
    );

    let mut bad = encoded;
    bad[40] = (PUBLIC_INPUT_COUNT - 1) as u8;
    assert_eq!(
        BundleProofEnvelope::decode(&bad).unwrap_err(),
        EnvelopeError::WrongInstanceCount
    );
}

#[test]
fn noncanonical_field_is_rejected() {
    let mut encoded = fixture().encode().expect("encode");
    let first_field = 41;
    encoded[first_field..first_field + 32].fill(0xff);
    assert_eq!(
        BundleProofEnvelope::decode(&encoded).unwrap_err(),
        EnvelopeError::NonCanonicalField
    );
}

#[test]
fn truncation_and_trailing_bytes_are_rejected() {
    let encoded = fixture().encode().expect("encode");

    let truncated = &encoded[..encoded.len() - 1];
    assert_eq!(
        BundleProofEnvelope::decode(truncated).unwrap_err(),
        EnvelopeError::Truncated
    );

    let mut trailing = encoded;
    trailing.push(0);
    assert_eq!(
        BundleProofEnvelope::decode(&trailing).unwrap_err(),
        EnvelopeError::TrailingBytes
    );
}

#[test]
fn empty_and_oversized_proofs_fail_closed() {
    let public_inputs: [Fp; PUBLIC_INPUT_COUNT] =
        core::array::from_fn(|index| Fp::from((index as u64) + 1));

    assert_eq!(
        BundleProofEnvelope::new([0; 32], public_inputs, vec![]).unwrap_err(),
        EnvelopeError::EmptyProof
    );

    let public_inputs: [Fp; PUBLIC_INPUT_COUNT] =
        core::array::from_fn(|index| Fp::from((index as u64) + 1));
    assert_eq!(
        BundleProofEnvelope::new(
            [0; 32],
            public_inputs,
            vec![0; MAX_PROOF_BYTES + 1]
        )
        .unwrap_err(),
        EnvelopeError::ProofTooLarge
    );
}
