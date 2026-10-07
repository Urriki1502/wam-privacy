use std::{ptr, sync::OnceLock, time::Instant};

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
    serialization_v2::{
        vk_identifier, HardenedBundleEnvelope, MAX_PROOF_BYTES, PUBLIC_INPUT_COUNT,
    },
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

fn build_proof_envelope() -> (Vec<u8>, ProofContext, [u8; 32]) {
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

    let envelope = HardenedBundleEnvelope::new(pk.get_vk(), public_array, proof).expect("envelope");
    (envelope.encode().expect("encode"), context, expected_vk_id)
}

fn proof_envelope() -> (Vec<u8>, ProofContext, [u8; 32]) {
    static FIXTURE: OnceLock<(Vec<u8>, ProofContext, [u8; 32])> = OnceLock::new();
    FIXTURE.get_or_init(build_proof_envelope).clone()
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
fn core_facing_ffi_contract() {
    assert_eq!(wam_privacy_halo2_abi_version(), ABI_VERSION);

    let (encoded, context, expected_vk_id) = proof_envelope();
    let handle = unsafe { new_handle() };

    let mut actual_vk_id = [0u8; 32];
    assert_eq!(
        unsafe {
            wam_privacy_halo2_verifier_vk_id(handle, actual_vk_id.as_mut_ptr(), actual_vk_id.len())
        },
        FfiStatus::Ok as i32
    );
    assert_eq!(actual_vk_id, expected_vk_id);

    assert!(encoded.len() <= MAX_PROOF_BYTES + 1024);
    let verify_start = Instant::now();
    let valid = unsafe {
        wam_privacy_halo2_verify_hardened_v1(
            handle,
            encoded.as_ptr(),
            encoded.len(),
            NetworkId::Regtest as u32,
            context.transaction_digest.as_ptr(),
            32,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        )
    };
    assert_eq!(valid, FfiStatus::Ok as i32);
    eprintln!("PHASE13D_ENVELOPE_BYTES={}", encoded.len());
    eprintln!(
        "PHASE13D_VERIFY_MICROS={}",
        verify_start.elapsed().as_micros()
    );

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

    let malformed = [0xFFu8; 16];
    let malformed_rc = unsafe {
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
    assert_eq!(malformed_rc, FfiStatus::BadEnvelope as i32);

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


#[test]
fn phase14b_adversarial_verifier_corpus_fails_closed() {
    let (encoded, context, _) = proof_envelope();
    let handle = unsafe { new_handle() };

    let verify = |candidate: &[u8], digest: &[u8; 32], transparent_in: u64,
                  transparent_out: u64, fee: u64| -> i32 {
        unsafe {
            wam_privacy_halo2_verify_hardened_v1(
                handle,
                candidate.as_ptr(),
                candidate.len(),
                NetworkId::Regtest as u32,
                digest.as_ptr(),
                digest.len(),
                transparent_in,
                transparent_out,
                fee,
            )
        }
    };

    assert_eq!(
        verify(
            &encoded,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::Ok as i32
    );

    let mut bad_magic = encoded.clone();
    bad_magic[0] ^= 1;
    assert_eq!(
        verify(
            &bad_magic,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::BadEnvelope as i32
    );

    let mut bad_version = encoded.clone();
    bad_version[4] ^= 1;
    assert_eq!(
        verify(
            &bad_version,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::BadEnvelope as i32
    );

    let mut bad_count = encoded.clone();
    bad_count[40] = 0;
    assert_eq!(
        verify(
            &bad_count,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::BadEnvelope as i32
    );

    let mut noncanonical_field = encoded.clone();
    noncanonical_field[41..73].fill(0xff);
    assert_eq!(
        verify(
            &noncanonical_field,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::BadEnvelope as i32
    );

    let mut wrong_vk = encoded.clone();
    wrong_vk[8] ^= 1;
    assert_eq!(
        verify(
            &wrong_vk,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::VkIdMismatch as i32
    );

    let mut bad_fee = encoded.clone();
    let fee_field = 41 + 5 * 32;
    bad_fee[fee_field] ^= 1;
    assert_eq!(
        verify(
            &bad_fee,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::TransparentBalanceMismatch as i32
    );

    let mut trailing = encoded.clone();
    trailing.push(0);
    assert_eq!(
        verify(
            &trailing,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::BadEnvelope as i32
    );

    let mut truncated = encoded.clone();
    truncated.pop();
    assert_eq!(
        verify(
            &truncated,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::BadEnvelope as i32
    );

    let mut wrong_digest = context.transaction_digest;
    wrong_digest[0] ^= 1;
    assert_eq!(
        verify(
            &encoded,
            &wrong_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::ContextMismatch as i32
    );

    let mut tampered_proof = encoded.clone();
    *tampered_proof.last_mut().expect("proof byte") ^= 1;
    assert_eq!(
        verify(
            &tampered_proof,
            &context.transaction_digest,
            context.transparent_in,
            context.transparent_out,
            context.fee,
        ),
        FfiStatus::ProofRejected as i32
    );

    assert_eq!(
        unsafe { wam_privacy_halo2_verifier_free(handle) },
        FfiStatus::Ok as i32
    );
}
