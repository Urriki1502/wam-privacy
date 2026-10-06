use halo2_proofs::{dev::MockProver, pasta::Fp};
use wam_privacy_halo2_prototype::anchor::{
    merkle_root, AnchorCircuit, TREE_DEPTH,
};

const K: u32 = 12;

fn fixture() -> AnchorCircuit {
    AnchorCircuit {
        leaf: Fp::from(101),
        siblings: [
            Fp::from(201),
            Fp::from(202),
            Fp::from(203),
            Fp::from(204),
        ],
        directions: [false, true, false, true],
    }
}

fn assert_pass(circuit: AnchorCircuit, public_root: Fp) {
    let prover =
        MockProver::run(K, &circuit, vec![vec![public_root]]).expect("mock prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: AnchorCircuit, public_root: Fp) {
    let prover =
        MockProver::run(K, &circuit, vec![vec![public_root]]).expect("mock prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn valid_private_path_binds_to_public_anchor() {
    let circuit = fixture();
    assert_pass(circuit.clone(), circuit.root());
}

#[test]
fn native_helper_matches_circuit_root() {
    let circuit = fixture();
    let expected = merkle_root(circuit.leaf, circuit.siblings, circuit.directions);
    assert_eq!(expected, circuit.root());
    assert_pass(circuit, expected);
}

#[test]
fn wrong_public_anchor_is_rejected() {
    let circuit = fixture();
    let wrong = circuit.root() + Fp::from(1);
    assert_fail(circuit, wrong);
}

#[test]
fn tampered_private_sibling_is_rejected_against_original_anchor() {
    let original = fixture();
    let root = original.root();
    let mut tampered = original.clone();
    tampered.siblings[2] += Fp::from(1);
    assert_fail(tampered, root);
}

#[test]
fn tampered_direction_bit_is_rejected_against_original_anchor() {
    let original = fixture();
    let root = original.root();
    let mut tampered = original.clone();
    tampered.directions[1] = !tampered.directions[1];
    assert_fail(tampered, root);
}

#[test]
fn all_left_path_is_supported() {
    let circuit = AnchorCircuit {
        leaf: Fp::from(11),
        siblings: [
            Fp::from(12),
            Fp::from(13),
            Fp::from(14),
            Fp::from(15),
        ],
        directions: [false; TREE_DEPTH],
    };
    assert_pass(circuit.clone(), circuit.root());
}

#[test]
fn all_right_path_is_supported() {
    let circuit = AnchorCircuit {
        leaf: Fp::from(21),
        siblings: [
            Fp::from(22),
            Fp::from(23),
            Fp::from(24),
            Fp::from(25),
        ],
        directions: [true; TREE_DEPTH],
    };
    assert_pass(circuit.clone(), circuit.root());
}
