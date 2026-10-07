use halo2_proofs::pasta::Fp;
use wam_privacy_halo2_prototype::{
    context::{NetworkId, ProofContext, CIRCUIT_ID_HARDENED_2X2, PROTOCOL_VERSION},
    ffi::ABI_VERSION,
    serialization::{BundleProofEnvelope, EnvelopeError},
    serialization_v2::{HardenedBundleEnvelope, HardenedEnvelopeError, PUBLIC_INPUT_COUNT},
};

fn legacy_v1_bytes() -> Vec<u8> {
    let public = core::array::from_fn(|i| Fp::from((i as u64) + 1));
    BundleProofEnvelope::new([0x11; 32], public, vec![1, 2, 3, 4])
        .expect("legacy fixture")
        .encode()
        .expect("legacy encode")
}

fn hardened_v2_bytes() -> Vec<u8> {
    let public: [Fp; PUBLIC_INPUT_COUNT] =
        core::array::from_fn(|i| Fp::from((i as u64) + 1));
    HardenedBundleEnvelope {
        vk_id: [0x22; 32],
        public_inputs: public,
        proof: vec![5, 6, 7, 8],
    }
    .encode()
    .expect("hardened encode")
}

#[test]
fn legacy_and_hardened_envelopes_are_not_cross_decoded() {
    assert_eq!(
        HardenedBundleEnvelope::decode(&legacy_v1_bytes()).unwrap_err(),
        HardenedEnvelopeError::BadMagic
    );
    assert_eq!(
        BundleProofEnvelope::decode(&hardened_v2_bytes()).unwrap_err(),
        EnvelopeError::BadMagic
    );
}

#[test]
fn unknown_future_format_and_circuit_fail_closed() {
    let encoded = hardened_v2_bytes();

    let mut bad_version = encoded.clone();
    bad_version[4..6].copy_from_slice(&(u16::MAX).to_le_bytes());
    assert_eq!(
        HardenedBundleEnvelope::decode(&bad_version).unwrap_err(),
        HardenedEnvelopeError::UnsupportedVersion
    );

    let mut bad_circuit = encoded;
    bad_circuit[6..8].copy_from_slice(&(CIRCUIT_ID_HARDENED_2X2 + 1).to_le_bytes());
    assert_eq!(
        HardenedBundleEnvelope::decode(&bad_circuit).unwrap_err(),
        HardenedEnvelopeError::UnsupportedCircuit
    );
}

#[test]
fn protocol_and_network_contexts_are_domain_separated() {
    let tx = [0x5A; 32];
    let regtest = ProofContext::new(NetworkId::Regtest, tx, 10, 2, 1);
    let testnet = ProofContext::new(NetworkId::Testnet, tx, 10, 2, 1);
    let mainnet = ProofContext::new(NetworkId::Mainnet, tx, 10, 2, 1);

    assert_ne!(regtest.digest(), testnet.digest());
    assert_ne!(regtest.digest(), mainnet.digest());
    assert_ne!(testnet.digest(), mainnet.digest());

    let mut future_protocol = regtest.clone();
    future_protocol.protocol_version = PROTOCOL_VERSION + 1;
    assert_ne!(regtest.digest(), future_protocol.digest());
}

#[test]
fn ffi_and_protocol_versions_are_explicit_nonzero_contracts() {
    assert_eq!(ABI_VERSION, 1);
    assert_eq!(PROTOCOL_VERSION, 1);
    assert_eq!(CIRCUIT_ID_HARDENED_2X2, 0x0A04);
}
