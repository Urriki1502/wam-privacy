use halo2_proofs::pasta::Fp;
use wam_privacy_halo2_prototype::{
    context::CIRCUIT_ID_HARDENED_2X2,
    serialization_v2::{
        HardenedBundleEnvelope, HardenedEnvelopeError, FORMAT_VERSION, MAGIC, MAX_PROOF_BYTES,
        PUBLIC_INPUT_COUNT,
    },
};

fn encoded_fixture() -> Vec<u8> {
    HardenedBundleEnvelope {
        vk_id: [0x11; 32],
        public_inputs: [Fp::zero(); PUBLIC_INPUT_COUNT],
        proof: vec![1, 2, 3, 4],
    }
    .encode()
    .expect("fixture")
}

#[test]
fn every_truncated_prefix_fails_closed() {
    let encoded = encoded_fixture();

    for cut in 0..encoded.len() {
        assert!(
            HardenedBundleEnvelope::decode(&encoded[..cut]).is_err(),
            "truncated prefix unexpectedly decoded at {cut}"
        );
    }

    assert!(HardenedBundleEnvelope::decode(&encoded).is_ok());
}

#[test]
fn oversized_declared_proof_is_rejected_before_payload_read() {
    let mut encoded = Vec::new();
    encoded.extend_from_slice(&MAGIC);
    encoded.extend_from_slice(&FORMAT_VERSION.to_le_bytes());
    encoded.extend_from_slice(&CIRCUIT_ID_HARDENED_2X2.to_le_bytes());
    encoded.extend_from_slice(&[0u8; 32]);
    encoded.push(PUBLIC_INPUT_COUNT as u8);
    encoded.extend_from_slice(&[0u8; PUBLIC_INPUT_COUNT * 32]);
    encoded.extend_from_slice(&((MAX_PROOF_BYTES as u32) + 1).to_le_bytes());

    assert_eq!(
        HardenedBundleEnvelope::decode(&encoded).unwrap_err(),
        HardenedEnvelopeError::ProofTooLarge
    );
}

#[test]
fn malformed_corpus_never_decodes() {
    for len in 0..4096usize {
        let mut candidate = vec![0u8; len];
        for (index, byte) in candidate.iter_mut().enumerate() {
            *byte = ((index * 131 + len * 17) & 0xff) as u8;
        }
        if candidate.len() >= 4 {
            candidate[0] = 0xFF;
        }
        assert!(HardenedBundleEnvelope::decode(&candidate).is_err());
    }
}
