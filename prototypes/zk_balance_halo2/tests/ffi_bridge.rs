use std::{ptr, sync::OnceLock};

use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{create_proof, keygen_pk, keygen_vk},
    poly::commitment::Params,
    transcript::{Blake2bWrite, Challenge255},
};
use rand_core::OsRng;
use wam_privacy_halo2_prototype::{
    context::{NetworkId, ProofContext},
    ffi::{
        wam_privacy_halo2_abi_version, wam_privacy_halo2_verifier_free,
        wam_privacy_halo2_verifier_new, wam_privacy_halo2_verifier_vk_id,
        wam_privacy_halo2_verify_hardened_v1, FfiStatus, WamPrivacyVerifier, ABI_VERSION,
        VERIFIER_K,
    },
    hardened_bundle::{HardenedBundleCircuit, HardenedBundleInput, HardenedBundleOutput},
    note_action::authority_tag,
    serialization_v2::{vk_identifier, HardenedBundleEnvelope, PUBLIC_INPUT_COUNT},
    MAX_WAM_ATOMS,
};

fn fixture() -> (HardenedBundleCircuit, ProofContext) {
    let fee = 3_000;
    let transparent_in = 10_000;
    let transparent_out = 2_000;
    let context = ProofContext::new(
        NetworkId::Regtest,
        [0xA5; 32],
        transparent_in,
        transparent_out,
        fee,
    );
    let mut circuit = HardenedBundleCircuit {
        inputs: [
            HardenedBundleInput {
                value: 50_000,
                recipient_tag: Fp::from(0x1111),
                spend_secret: Fp::from(0x2222),
                rho: Fp::from(0x3333),
                rseed: Fp::from(0x4444),
                siblings: [Fp::from(0); 4],
                directions: [false; 4],
            },
            HardenedBundleInput {
                value: 50_000,
                recipient_tag: Fp::from(0x1212),
                spend_secret: Fp::from(0x2323),
                rho: Fp::from(0x3434),
                rseed: Fp::from(0x4545),
                siblings: [Fp::from(0); 4],
                directions: [false; 4],
            },
        ],
        outputs: [
            HardenedBundleOutput {
                value: 52_500,
                recipient_tag: Fp::from(0x5555),
                spend_authority_tag: authority_tag(Fp::from(0x6666)),
                rho: Fp::from(0x7777),
                rseed: Fp::from(0x8888),
            },
            HardenedBundleOutput {
                value: 52_500,
                recipient_tag: Fp::from(0x5959),
                spend_authority_tag: authority_tag(Fp::from(0x6969)),
                rho: Fp::from(0x7979),
                rseed: Fp::from(0x8989),
            },
        ],
        fee,
        transparent_in,
        transparent_out,
        context_digest: context.digest(),
    };

    let id0 = circuit.inputs[0].identity();
    let id1 = circuit.inputs[1].identity();
    let upper = [Fp::from(701), Fp::from(702), Fp::from(703)];

    circuit.inputs[0].siblings = [id1, upper[0], upper[1], upper[2]];
    circuit.inputs[0].directions = [false, false, true, false];

    circuit.inputs[1].siblings = [id0, upper[0], upper[1], upper[2]];
    circuit.inputs[1].directions = [true, false, true, false];

    assert_eq!(circuit.inputs[0].root(), circuit.inputs[1].root());
    (circuit, context)
}

fn proof_envelope() -> (Vec<u8>, ProofContext, [u8; 32]) {
    static FIXTURE: OnceLock<(Vec<u8>, ProofContext, [u8; 32])> = OnceLock::new();
    FIXTURE
        .get_or_init(|| {
            let (circuit, context) = fixture();
    let public = circuit.public_inputs();
    let public_array: [Fp; PUBLIC_INPUT_COUNT] =
        public.clone().try_into().expect("nine public inputs");

    let params: Params<EqAffine> = Params::new(VERIFIER_K);
    let vk = keygen_vk(&params, &circuit).expect("verification key");
    let expected_vk_id = vk_identifier(&vk);
    let pk = keygen_pk(&params, vk, &circuit).expect("proving key");

    let instance_columns: &[&[Fp]] = &[&public];
    let mut transcript = Blake2bWrite::<_, EqAffine, Challenge255<_>>::init(vec![]);
    create_proof(
        &params,
        &pk,
        &[circuit],
        &[instance_columns],
        OsRng,
        &mut transcript,
    )
    .expect("proof");
    let proof = transcript.finalize();

            let envelope =
                HardenedBundleEnvelope::new(pk.get_vk(), public_array, proof).expect("envelope");
            (envelope.encode().expect("encode"), context, expected_vk_id)
        })
        .clone()
}

unsafe fn new_handle() -> *mut WamPrivacyVerifier {
    let mut handle = ptr::null_mut();
    assert_eq!(
        unsafe { wam_privacy_halo2_verifier_new(&mut handle) },
        FfiStatus::Ok as i32
    );
    assert!(!handle.is_null());
    handle
}

#[test]
fn abi_version_and_vk_identity_are_stable() {
    assert_eq!(wam_privacy_halo2_abi_version(), ABI_VERSION);
    let (_, _, expected_vk_id) = proof_envelope();
    let handle = unsafe { new_handle() };

    let mut actual = [0u8; 32];
    assert_eq!(
        unsafe { wam_privacy_halo2_verifier_vk_id(handle, actual.as_mut_ptr(), actual.len()) },
        FfiStatus::Ok as i32
    );
    assert_eq!(actual, expected_vk_id);

    assert_eq!(
        unsafe { wam_privacy_halo2_verifier_free(handle) },
        FfiStatus::Ok as i32
    );
}

#[test]
fn real_hardened_proof_verifies_through_core_facing_abi() {
    let (encoded, context, _) = proof_envelope();
    let handle = unsafe { new_handle() };

    let rc = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            encoded.as_ptr(),
            encoded.len(),
            NetworkId::Regtest as u32,
            context.transaction_digest.as_ptr(),
            context.transaction_digest.len(),
            context.transparent_in,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(rc, FfiStatus::Ok as i32);

    assert_eq!(
        unsafe { wam_privacy_halo2_verifier_free(handle) },
        FfiStatus::Ok as i32
    );
}

#[test]
fn context_and_network_replay_fail_closed() {
    let (encoded, context, _) = proof_envelope();
    let handle = unsafe { new_handle() };

    let mainnet = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            encoded.as_ptr(),
            encoded.len(),
            NetworkId::Mainnet as u32,
            context.transaction_digest.as_ptr(),
            32,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(mainnet, FfiStatus::UnsupportedNetwork as i32);

    let mut wrong_digest = context.transaction_digest;
    wrong_digest[0] ^= 1;
    let wrong_tx = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            encoded.as_ptr(),
            encoded.len(),
            NetworkId::Regtest as u32,
            wrong_digest.as_ptr(),
            32,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(wrong_tx, FfiStatus::ContextMismatch as i32);

    let wrong_balance = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            encoded.as_ptr(),
            encoded.len(),
            NetworkId::Regtest as u32,
            context.transaction_digest.as_ptr(),
            32,
            context.transparent_in + 1,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(wrong_balance, FfiStatus::ContextMismatch as i32);

    assert_eq!(
        unsafe { wam_privacy_halo2_verifier_free(handle) },
        FfiStatus::Ok as i32
    );
}

#[test]
fn malformed_inputs_fail_before_or_during_verification() {
    let (encoded, context, _) = proof_envelope();
    let handle = unsafe { new_handle() };

    let malformed = [0xFFu8; 16];
    let rc = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            malformed.as_ptr(),
            malformed.len(),
            NetworkId::Regtest as u32,
            context.transaction_digest.as_ptr(),
            32,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(rc, FfiStatus::BadEnvelope as i32);

    let bad_digest_len = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            encoded.as_ptr(),
            encoded.len(),
            NetworkId::Regtest as u32,
            context.transaction_digest.as_ptr(),
            31,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(bad_digest_len, FfiStatus::BadLength as i32);

    let bad_amount = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            encoded.as_ptr(),
            encoded.len(),
            NetworkId::Regtest as u32,
            context.transaction_digest.as_ptr(),
            32,
            MAX_WAM_ATOMS + 1,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(bad_amount, FfiStatus::AmountRange as i32);

    assert_eq!(
        unsafe { wam_privacy_halo2_verifier_free(handle) },
        FfiStatus::Ok as i32
    );
}
