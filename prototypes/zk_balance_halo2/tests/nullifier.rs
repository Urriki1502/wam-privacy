use halo2_proofs::{dev::MockProver, pasta::Fp};
use wam_privacy_halo2_prototype::nullifier::{authority_tag, nullifier, NullifierCircuit};

const K: u32 = 10;

fn fixture() -> NullifierCircuit {
    NullifierCircuit {
        spend_secret: Fp::from(0x1234_5678),
        note_identity: Fp::from(0x00ab_cdef),
    }
}

fn assert_pass(circuit: NullifierCircuit, public: Vec<Fp>) {
    let prover = MockProver::run(K, &circuit, vec![public]).expect("mock prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: NullifierCircuit, public: Vec<Fp>) {
    let prover =
        MockProver::run(K, &circuit, vec![public]).expect("mock prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn correct_private_authority_and_note_bind_to_public_outputs() {
    let circuit = fixture();
    assert_pass(circuit.clone(), circuit.public_inputs());
}

#[test]
fn wrong_private_spend_authority_fails_original_public_outputs() {
    let original = fixture();
    let public = original.public_inputs();

    let tampered = NullifierCircuit {
        spend_secret: original.spend_secret + Fp::from(1),
        note_identity: original.note_identity,
    };

    assert_fail(tampered, public);
}

#[test]
fn wrong_private_note_identity_fails_original_nullifier() {
    let original = fixture();
    let public = original.public_inputs();

    let tampered = NullifierCircuit {
        spend_secret: original.spend_secret,
        note_identity: original.note_identity + Fp::from(1),
    };

    assert_fail(tampered, public);
}

#[test]
fn same_authority_on_different_notes_has_same_tag_but_different_nullifier() {
    let secret = Fp::from(777);
    let note_a = Fp::from(1001);
    let note_b = Fp::from(1002);

    assert_eq!(authority_tag(secret), authority_tag(secret));
    assert_ne!(nullifier(secret, note_a), nullifier(secret, note_b));
}

#[test]
fn different_authorities_have_different_tags_and_nullifiers() {
    let note_id = Fp::from(9090);
    let a = Fp::from(111);
    let b = Fp::from(222);

    assert_ne!(authority_tag(a), authority_tag(b));
    assert_ne!(nullifier(a, note_id), nullifier(b, note_id));
}

#[test]
fn swapping_public_tag_and_nullifier_rows_is_rejected() {
    let circuit = fixture();
    let public = circuit.public_inputs();
    assert_fail(circuit, vec![public[1], public[0]]);
}
