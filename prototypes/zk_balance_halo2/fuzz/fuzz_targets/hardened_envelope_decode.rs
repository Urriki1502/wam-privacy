#![no_main]

use libfuzzer_sys::fuzz_target;
use wam_privacy_halo2_prototype::serialization_v2::HardenedBundleEnvelope;

fuzz_target!(|data: &[u8]| {
    if let Ok(decoded) = HardenedBundleEnvelope::decode(data) {
        let encoded = decoded.encode().expect("decoded envelope must re-encode");
        let roundtrip =
            HardenedBundleEnvelope::decode(&encoded).expect("canonical re-encoding must decode");

        assert_eq!(roundtrip.vk_id, decoded.vk_id);
        assert_eq!(roundtrip.public_inputs, decoded.public_inputs);
        assert_eq!(roundtrip.proof, decoded.proof);
        assert_eq!(encoded, roundtrip.encode().expect("stable canonical encoding"));
    }
});
