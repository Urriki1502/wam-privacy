use halo2_proofs::{dev::MockProver, pasta::Fp};
use wam_privacy_halo2_prototype::{
    context::{NetworkId, ProofContext},
    hardened_bundle::{HardenedBundleCircuit, HardenedBundleInput, HardenedBundleOutput},
    note_action::authority_tag,
    MAX_WAM_ATOMS,
};

const K: u32 = 15;

fn reanchor(circuit: &mut HardenedBundleCircuit) {
    let id0 = circuit.inputs[0].identity();
    let id1 = circuit.inputs[1].identity();
    let upper = [Fp::from(701), Fp::from(702), Fp::from(703)];

    circuit.inputs[0].siblings = [id1, upper[0], upper[1], upper[2]];
    circuit.inputs[0].directions = [false, false, true, false];
    circuit.inputs[1].siblings = [id0, upper[0], upper[1], upper[2]];
    circuit.inputs[1].directions = [true, false, true, false];

    assert_eq!(circuit.inputs[0].root(), circuit.inputs[1].root());
}

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
    reanchor(&mut circuit);
    (circuit, context)
}

fn assert_pass(circuit: HardenedBundleCircuit) {
    let public = circuit.public_inputs();
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase10d prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: HardenedBundleCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase10d prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn hardened_bundle_binds_transparent_flow_and_context() {
    let (circuit, _) = fixture();
    assert_eq!(circuit.input_total(), 110_000);
    assert_eq!(circuit.output_total_with_fee(), 110_000);
    assert_eq!(circuit.public_inputs().len(), 9);
    assert_pass(circuit);
}

#[test]
fn authority_tags_are_not_public_instances() {
    let (circuit, _) = fixture();
    let public = circuit.public_inputs();
    assert!(!public.contains(&circuit.inputs[0].authority_tag()));
    assert!(!public.contains(&circuit.inputs[1].authority_tag()));
    assert_eq!(public[1], circuit.inputs[0].nullifier());
    assert_eq!(public[2], circuit.inputs[1].nullifier());
}

#[test]
fn context_tampering_is_rejected_by_the_circuit_relation() {
    let (circuit, _) = fixture();
    let public = circuit.public_inputs();
    let mut changed = circuit;
    changed.context_digest += Fp::from(1);
    assert_fail(changed, public);
}

#[test]
fn transparent_value_imbalance_is_rejected() {
    let (mut circuit, _) = fixture();
    circuit.transparent_out += 1;
    let public = circuit.public_inputs();
    assert_fail(circuit, public);
}

#[test]
fn duplicate_nullifiers_and_outputs_still_fail_closed() {
    let (mut duplicate_input, _) = fixture();
    duplicate_input.inputs[1] = duplicate_input.inputs[0].clone();
    reanchor(&mut duplicate_input);
    let public = duplicate_input.public_inputs();
    assert_eq!(public[1], public[2]);
    assert_fail(duplicate_input, public);

    let (mut duplicate_output, _) = fixture();
    duplicate_output.outputs[1] = duplicate_output.outputs[0].clone();
    let public = duplicate_output.public_inputs();
    assert_eq!(public[3], public[4]);
    assert_fail(duplicate_output, public);
}

#[test]
fn aggregate_cap_including_transparent_flow_is_enforced() {
    let (mut circuit, _) = fixture();
    circuit.inputs[0].value = MAX_WAM_ATOMS;
    circuit.inputs[1].value = 1;
    circuit.transparent_in = 1;
    circuit.outputs[0].value = MAX_WAM_ATOMS - 1;
    circuit.outputs[1].value = 1;
    circuit.transparent_out = 1;
    circuit.fee = 1;
    reanchor(&mut circuit);
    let public = circuit.public_inputs();
    assert!(circuit.input_total() > MAX_WAM_ATOMS);
    assert_fail(circuit, public);
}
