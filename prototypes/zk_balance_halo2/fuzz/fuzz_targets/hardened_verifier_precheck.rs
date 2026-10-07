#![no_main]

use libfuzzer_sys::fuzz_target;
use wam_privacy_halo2_prototype::{
    context::{NetworkId, ProofContext},
    serialization_v2::precheck_hardened_bundle_envelope,
};

fuzz_target!(|data: &[u8]| {
    let context = ProofContext::new(NetworkId::Regtest, [0x42; 32], 11, 7, 4);
    let _ = precheck_hardened_bundle_envelope([0xA5; 32], &context, data);
});
