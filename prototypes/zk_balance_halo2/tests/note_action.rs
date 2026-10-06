use halo2_proofs::{dev::MockProver, pasta::Fp};
use wam_privacy_halo2_prototype::{
    note_action::{note_identity, NoteActionCircuit},
    MAX_WAM_ATOMS,
};

const K: u32 = 14;

fn fixture() -> NoteActionCircuit {
    NoteActionCircuit {
        value: 125_000,
        recipient_tag: Fp::from(0x1111),
        spend_secret: Fp::from(0x2222),
        rho: Fp::from(0x3333),
        rseed: Fp::from(0x4444),
        siblings: [Fp::from(201), Fp::from(202), Fp::from(203), Fp::from(204)],
        directions: [false, true, false, true],
    }
}

fn assert_pass(circuit: NoteActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase9b prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: NoteActionCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("phase9b prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn complete_private_note_fields_derive_anchored_nullified_identity() {
    let circuit = fixture();
    assert_pass(circuit.clone(), circuit.public_inputs());
}

#[test]
fn native_identity_is_deterministic_and_complete() {
    let circuit = fixture();
    let tag = wam_privacy_halo2_prototype::note_action::authority_tag(circuit.spend_secret);
    assert_eq!(
        circuit.native_note_identity(),
        note_identity(
            circuit.value,
            circuit.recipient_tag,
            tag,
            circuit.rho,
            circuit.rseed
        )
    );
}

#[test]
fn changing_each_note_field_invalidates_original_public_relation() {
    let original = fixture();
    let public = original.public_inputs();

    let mut changed = original.clone();
    changed.value += 1;
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.recipient_tag += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.spend_secret += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original.clone();
    changed.rho += Fp::from(1);
    assert_fail(changed, public.clone());

    let mut changed = original;
    changed.rseed += Fp::from(1);
    assert_fail(changed, public);
}

#[test]
fn zero_value_note_is_rejected() {
    let mut circuit = fixture();
    circuit.value = 0;
    let public = circuit.public_inputs();
    assert_fail(circuit, public);
}

#[test]
fn exact_wam_cap_is_accepted() {
    let mut circuit = fixture();
    circuit.value = MAX_WAM_ATOMS;
    assert_pass(circuit.clone(), circuit.public_inputs());
}

#[test]
fn one_atom_over_wam_cap_is_rejected() {
    let mut circuit = fixture();
    circuit.value = MAX_WAM_ATOMS + 1;
    let public = circuit.public_inputs();
    assert_fail(circuit, public);
}

#[test]
fn distinct_rho_or_rseed_changes_note_identity() {
    let original = fixture();

    let mut rho_changed = original.clone();
    rho_changed.rho += Fp::from(1);
    assert_ne!(
        original.native_note_identity(),
        rho_changed.native_note_identity()
    );

    let mut rseed_changed = original.clone();
    rseed_changed.rseed += Fp::from(1);
    assert_ne!(
        original.native_note_identity(),
        rseed_changed.native_note_identity()
    );
}
