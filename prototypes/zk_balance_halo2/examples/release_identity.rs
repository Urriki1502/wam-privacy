use halo2_proofs::{pasta::EqAffine, plonk::keygen_vk, poly::commitment::Params};
use wam_privacy_halo2_prototype::{
    context::{CIRCUIT_ID_HARDENED_2X2, PROTOCOL_VERSION},
    ffi::VERIFIER_K,
    hardened_bundle::HardenedBundleCircuit,
    serialization_v2::vk_identifier,
};

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write;
        write!(&mut out, "{byte:02x}").expect("write to String");
    }
    out
}

fn main() {
    let params: Params<EqAffine> = Params::new(VERIFIER_K);
    let circuit = HardenedBundleCircuit::default();
    let vk = keygen_vk(&params, &circuit).expect("deterministic verification key generation");
    let vk_id = vk_identifier(&vk);

    println!("protocol_version={PROTOCOL_VERSION}");
    println!("circuit_id={CIRCUIT_ID_HARDENED_2X2}");
    println!("verifier_k={VERIFIER_K}");
    println!("vk_id={}", hex(&vk_id));
}
