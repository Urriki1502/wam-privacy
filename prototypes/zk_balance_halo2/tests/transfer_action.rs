use halo2_proofs::{dev::MockProver, pasta::Fp};
use wam_privacy_halo2_prototype::{
    note_action::authority_tag, transfer_action::TransferActionCircuit, MAX_WAM_ATOMS,
};

const K: u32 = 15;

fn fixture() -> TransferActionCircuit {
    TransferActionCircuit {
        input_value: 125_000,
        input_recipient_tag: Fp::from(0x1111),
        spend_secret: Fp::from(0x2222),
        input_rho: Fp::from(0x3333),
        input_rseed: Fp::from(0x4444),
        siblings: [Fp::from(201), Fp::from(202), Fp::from(203), Fp::from(204)],
        directions: [false, true, false, true],
        output_value: 124_000,
        output_recipient_tag: Fp::from(0x5555),
        output_spend_authority_tag: authority_tag(Fp::from(0x6666)),
        output_rho: Fp::from(0x7777),
        output_rseed: Fp::from(0x8888),
        fee: 1_000,
    }
}

fn assert_pass(circuit: TransferActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase9c prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: TransferActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase9c prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn integrated_transfer_binds_spend_create_and_fee() {
    let circuit = fixture();
    assert_pass(circuit.clone(), circuit.public_inputs());
}

#[test]
fn unbalanced_value_relation_is_rejected() {
    let original = fixture();
    let public = original.public_inputs();

    let mut changed = original;
    changed.output_value += 1;
    assert_fail(changed, public);
}

#[test]
fn output_note_fields_are_bound_to_public_commitment() {
    let original = fixture();
    let public = original.public_inputs();

    let mut changed = original.clone();
    changed.output_recipient_tag += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.output_spend_authority_tag += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.output_rho += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original;
    changed.output_rseed += Fp::from(1);
    assert_fail(changed, public);
}

#[test]
fn input_note_and_authority_remain_bound() {
    let original = fixture();
    let public = original.public_inputs();

    let mut changed = original.clone();
    changed.input_recipient_tag += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.input_rho += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.input_rseed += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original;
    changed.spend_secret += Fp::from(1);
    assert_fail(changed, public);
}

#[test]
fn fee_is_publicly_bound() {
    let circuit = fixture();
    let mut public = circuit.public_inputs();
    public[4] += Fp::from(1);
    assert_fail(circuit, public);
}

#[test]
fn output_commitment_is_publicly_bound() {
    let circuit = fixture();
    let mut public = circuit.public_inputs();
    public[3] += Fp::from(1);
    assert_fail(circuit, public);
}

#[test]
fn zero_shielded_values_are_rejected() {
    let original = fixture();

    let mut zero_input = original.clone();
    zero_input.input_value = 0;
    zero_input.output_value = 0;
    zero_input.fee = 0;
    let public = zero_input.public_inputs();
    assert_fail(zero_input, public);

    let mut zero_output = original;
    zero_output.output_value = 0;
    zero_output.fee = zero_output.input_value;
    let public = zero_output.public_inputs();
    assert_fail(zero_output, public);
}

#[test]
fn exact_cap_is_supported_without_inflation() {
    let mut circuit = fixture();
    circuit.input_value = MAX_WAM_ATOMS;
    circuit.fee = 1_000;
    circuit.output_value = MAX_WAM_ATOMS - circuit.fee;
    assert_pass(circuit.clone(), circuit.public_inputs());
}

#[test]
fn one_atom_over_cap_is_rejected() {
    let mut circuit = fixture();
    circuit.input_value = MAX_WAM_ATOMS + 1;
    circuit.output_value = MAX_WAM_ATOMS;
    circuit.fee = 1;
    let public = circuit.public_inputs();
    assert_fail(circuit, public);
}

#[test]
fn merkle_path_remains_bound_to_input_identity() {
    let original = fixture();
    let public = original.public_inputs();

    let mut changed = original.clone();
    changed.siblings[1] += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original;
    changed.directions[2] = !changed.directions[2];
    assert_fail(changed, public);
}
