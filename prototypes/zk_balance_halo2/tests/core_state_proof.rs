use ff::PrimeField;
use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{create_proof, keygen_pk, keygen_vk},
    poly::commitment::Params,
    transcript::{Blake2bWrite, Challenge255},
};
use rand_core::OsRng;
use wam_privacy_halo2_prototype::{
    context::{NetworkId, ProofContext},
    core_state::{CoreShieldedState, StateBlock, VerifiedTransition},
    hardened_bundle::{HardenedBundleCircuit, HardenedBundleInput, HardenedBundleOutput},
    note_action::authority_tag,
    serialization_v2::{HardenedBundleEnvelope, PUBLIC_INPUT_COUNT},
};

const K: u32 = 15;

fn fp_bytes(value: Fp) -> [u8; 32] {
    let repr = value.to_repr();
    let mut out = [0u8; 32];
    out.copy_from_slice(repr.as_ref());
    out
}

fn fixture() -> (HardenedBundleCircuit, ProofContext) {
    let fee = 3_000;
    let transparent_in = 10_000;
    let transparent_out = 2_000;
    let context = ProofContext::new(
        NetworkId::Regtest,
        [0xC3; 32],
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
                siblings: [Fp::zero(); 4],
                directions: [false; 4],
            },
            HardenedBundleInput {
                value: 50_000,
                recipient_tag: Fp::from(0x1212),
                spend_secret: Fp::from(0x2323),
                rho: Fp::from(0x3434),
                rseed: Fp::from(0x4545),
                siblings: [Fp::zero(); 4],
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

    (circuit, context)
}

#[test]
fn verified_proof_metadata_drives_atomic_state_and_rollback() {
    let (circuit, context) = fixture();
    let public = circuit.public_inputs();
    let public_array: [Fp; PUBLIC_INPUT_COUNT] =
        public.clone().try_into().expect("nine public instances");

    let params: Params<EqAffine> = Params::new(K);
    let vk = keygen_vk(&params, &circuit).expect("verification key");
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
    let encoded = envelope.encode().expect("canonical encode");

    let verified =
        VerifiedTransition::from_verified_envelope(&params, pk.get_vk(), &context, &encoded)
            .expect("verified transition");

    let initial_pool = 100_000;
    let mut state = CoreShieldedState::new(verified.anchor(), initial_pool).expect("initial state");
    let before = state.clone();

    let block = StateBlock {
        height: 0,
        hash: [0x11; 32],
        prev_hash: [0u8; 32],
        next_anchor: fp_bytes(Fp::from(9_001)),
        transitions: vec![verified.clone()],
    };

    state.apply_block(block).expect("atomic apply");
    assert_eq!(
        state.pool_atoms(),
        initial_pool + context.transparent_in - context.transparent_out - context.fee
    );
    assert_eq!(state.nullifier_count(), 2);
    assert_eq!(state.commitment_count(), 2);

    state
        .disconnect_tip([0x11; 32])
        .expect("disconnect exact tip");
    assert_eq!(state, before);

    let mut tampered = HardenedBundleEnvelope::decode(&encoded).expect("decode");
    tampered.public_inputs[1] += Fp::from(1);
    let tampered = tampered.encode().expect("tampered encode");
    assert!(
        VerifiedTransition::from_verified_envelope(&params, pk.get_vk(), &context, &tampered)
            .is_err()
    );
}
