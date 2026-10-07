use halo2_proofs::{dev::MockProver, pasta::Fp};
use wam_privacy_halo2_prototype::{
    bundle_action::{BundleActionCircuit, BundleInput, BundleOutput},
    note_action::authority_tag,
    MAX_WAM_ATOMS,
};

const K: u32 = 15;

fn reanchor(circuit: &mut BundleActionCircuit) {
    let id0 = circuit.inputs[0].identity();
    let id1 = circuit.inputs[1].identity();
    let upper = [Fp::from(701), Fp::from(702), Fp::from(703)];

    circuit.inputs[0].siblings = [id1, upper[0], upper[1], upper[2]];
    circuit.inputs[0].directions = [false, false, true, false];

    circuit.inputs[1].siblings = [id0, upper[0], upper[1], upper[2]];
    circuit.inputs[1].directions = [true, false, true, false];

    assert_eq!(circuit.inputs[0].root(), circuit.inputs[1].root());
}

fn fixture() -> BundleActionCircuit {
    let mut circuit = BundleActionCircuit {
        inputs: [
            BundleInput {
                value: 50_000,
                recipient_tag: Fp::from(0x1111),
                spend_secret: Fp::from(0x2222),
                rho: Fp::from(0x3333),
                rseed: Fp::from(0x4444),
                siblings: [Fp::zero(); 4],
                directions: [false; 4],
            },
            BundleInput {
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
            BundleOutput {
                value: 47_500,
                recipient_tag: Fp::from(0x5555),
                spend_authority_tag: authority_tag(Fp::from(0x6666)),
                rho: Fp::from(0x7777),
                rseed: Fp::from(0x8888),
            },
            BundleOutput {
                value: 47_500,
                recipient_tag: Fp::from(0x5959),
                spend_authority_tag: authority_tag(Fp::from(0x6969)),
                rho: Fp::from(0x7979),
                rseed: Fp::from(0x8989),
            },
        ],
        fee: 5_000,
    };
    reanchor(&mut circuit);
    circuit
}

fn assert_pass(circuit: BundleActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase10b prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: BundleActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase10b prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn fixed_two_by_two_bundle_passes() {
    let circuit = fixture();
    assert_eq!(circuit.input_total(), 100_000);
    assert_eq!(circuit.output_total_with_fee(), 100_000);
    assert_pass(circuit.clone(), circuit.public_inputs());
}

#[test]
fn aggregate_value_imbalance_is_rejected() {
    let mut circuit = fixture();
    circuit.outputs[1].value += 1;
    let public = circuit.public_inputs();
    assert_fail(circuit, public);
}

#[test]
fn both_inputs_must_share_the_public_anchor() {
    let original = fixture();
    let public = original.public_inputs();

    let mut changed = original;
    changed.inputs[1].siblings[2] += Fp::from(1);
    assert_fail(changed, public);
}

#[test]
fn duplicate_nullifier_inside_bundle_is_rejected_in_circuit() {
    let mut circuit = fixture();
    circuit.inputs[1] = circuit.inputs[0].clone();
    reanchor(&mut circuit);
    let public = circuit.public_inputs();
    assert_eq!(public[2], public[4]);
    assert_fail(circuit, public);
}

#[test]
fn duplicate_output_commitment_is_rejected_in_circuit() {
    let mut circuit = fixture();
    circuit.outputs[1] = circuit.outputs[0].clone();
    let public = circuit.public_inputs();
    assert_eq!(public[5], public[6]);
    assert_fail(circuit, public);
}

#[test]
fn aggregate_wam_cap_is_enforced() {
    let mut circuit = fixture();
    circuit.inputs[0].value = MAX_WAM_ATOMS;
    circuit.inputs[1].value = 1;
    circuit.outputs[0].value = MAX_WAM_ATOMS - 1;
    circuit.outputs[1].value = 1;
    circuit.fee = 1;
    reanchor(&mut circuit);

    let public = circuit.public_inputs();
    assert_eq!(circuit.input_total(), MAX_WAM_ATOMS + 1);
    assert_eq!(circuit.output_total_with_fee(), MAX_WAM_ATOMS + 1);
    assert_fail(circuit, public);
}

#[test]
fn zero_shielded_values_are_rejected() {
    let mut zero_input = fixture();
    zero_input.inputs[0].value = 0;
    zero_input.outputs[0].value -= 50_000;
    zero_input.outputs[1].value += 50_000;
    reanchor(&mut zero_input);
    let public = zero_input.public_inputs();
    assert_fail(zero_input, public);

    let mut zero_output = fixture();
    zero_output.outputs[0].value = 0;
    zero_output.outputs[1].value = 95_000;
    let public = zero_output.public_inputs();
    assert_fail(zero_output, public);
}

#[test]
fn linked_private_fields_remain_bound() {
    let original = fixture();
    let public = original.public_inputs();

    let mut changed = original.clone();
    changed.inputs[1].recipient_tag += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.inputs[0].spend_secret += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.outputs[1].rho += Fp::from(1);
    assert_fail(changed, public);
}
