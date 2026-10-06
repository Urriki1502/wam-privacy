use halo2_proofs::{dev::MockProver, pasta::Fp};
use wam_privacy_halo2_prototype::action::ActionCircuit;

const K: u32 = 13;

fn fixture() -> ActionCircuit {
    ActionCircuit {
        spend_secret: Fp::from(0x1234_5678),
        note_identity: Fp::from(0x00ab_cdef),
        siblings: [Fp::from(201), Fp::from(202), Fp::from(203), Fp::from(204)],
        directions: [false, true, false, true],
    }
}

fn assert_pass(circuit: ActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("action prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: ActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("action prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn one_private_note_identity_binds_anchor_and_nullifier() {
    let circuit = fixture();
    assert_pass(circuit.clone(), circuit.public_inputs());
}

#[test]
fn changed_note_identity_fails_original_anchor_and_nullifier_relation() {
    let original = fixture();
    let public = original.public_inputs();

    let mut tampered = original;
    tampered.note_identity += Fp::from(1);

    assert_fail(tampered, public);
}

#[test]
fn changed_spend_authority_fails_original_public_relation() {
    let original = fixture();
    let public = original.public_inputs();

    let mut tampered = original;
    tampered.spend_secret += Fp::from(1);

    assert_fail(tampered, public);
}

#[test]
fn changed_merkle_sibling_fails_original_anchor_relation() {
    let original = fixture();
    let public = original.public_inputs();

    let mut tampered = original;
    tampered.siblings[2] += Fp::from(1);

    assert_fail(tampered, public);
}

#[test]
fn changed_direction_fails_original_anchor_relation() {
    let original = fixture();
    let public = original.public_inputs();

    let mut tampered = original;
    tampered.directions[1] = !tampered.directions[1];

    assert_fail(tampered, public);
}

#[test]
fn public_instance_order_is_part_of_the_contract() {
    let circuit = fixture();
    let public = circuit.public_inputs();
    assert_fail(circuit, vec![public[1], public[0], public[2]]);
}
