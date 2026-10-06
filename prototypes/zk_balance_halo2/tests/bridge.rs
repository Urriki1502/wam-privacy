use halo2_proofs::{dev::MockProver, pasta::Fp};
use serde::Deserialize;
use std::{fs, path::PathBuf};
use wam_privacy_halo2_prototype::{
    anchor::{merkle_root, AnchorCircuit},
    nullifier::{authority_tag, nullifier, NullifierCircuit},
    BalanceCircuit, MAX_WAM_ATOMS,
};

const BALANCE_K: u32 = 11;
const ANCHOR_K: u32 = 12;
const NULLIFIER_K: u32 = 10;

#[derive(Debug, Deserialize)]
struct Oracle {
    schema: u32,
    max_wam_atoms: u64,
    comparison_mode: String,
    phase7_tree_hash: String,
    phase8_tree_hash: String,
    balance_cases: Vec<BalanceCase>,
    properties: Properties,
}

#[derive(Debug, Deserialize)]
struct BalanceCase {
    name: String,
    spent: u64,
    transparent_in: u64,
    created: u64,
    transparent_out: u64,
    fee: u64,
    phase7_accepts: bool,
    phase7_error: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Properties {
    authority_mismatch_rejected: bool,
    same_authority_different_notes_have_distinct_nullifiers: bool,
    note_mutation_changes_commitment: bool,
    note_mutation_changes_root: bool,
    root_byte_compatibility_claimed: bool,
}

fn oracle() -> Oracle {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("bridge")
        .join("phase8f-oracle.json");
    let raw = fs::read_to_string(path).expect("Phase 8F oracle fixture");
    serde_json::from_str(&raw).expect("valid Phase 8F oracle JSON")
}

#[test]
fn phase7_balance_decisions_match_phase8_constraints() {
    let oracle = oracle();
    assert_eq!(oracle.schema, 1);
    assert_eq!(oracle.max_wam_atoms, MAX_WAM_ATOMS);
    assert_eq!(oracle.comparison_mode, "semantic-not-byte-equivalence");

    for case in oracle.balance_cases {
        let circuit = BalanceCircuit {
            spent: case.spent,
            transparent_in: case.transparent_in,
            created: case.created,
            transparent_out: case.transparent_out,
            fee: case.fee,
        };
        let prover = MockProver::run(BALANCE_K, &circuit, vec![])
            .unwrap_or_else(|err| panic!("{}: MockProver build failed: {err:?}", case.name));
        let phase8_accepts = prover.verify().is_ok();

        assert_eq!(
            phase8_accepts, case.phase7_accepts,
            "{}: Phase 7 error {:?}, Phase 8 acceptance {}",
            case.name, case.phase7_error, phase8_accepts
        );
    }
}

#[test]
fn phase7_relational_properties_have_phase8_equivalents() {
    let oracle = oracle();
    let props = oracle.properties;

    assert!(props.authority_mismatch_rejected);
    assert!(props.same_authority_different_notes_have_distinct_nullifiers);
    assert!(props.note_mutation_changes_commitment);
    assert!(props.note_mutation_changes_root);
    assert!(!props.root_byte_compatibility_claimed);

    // Authority mismatch semantics: changing private spend authority must not
    // satisfy the original public authority/nullifier relation.
    let original = NullifierCircuit {
        spend_secret: Fp::from(777),
        note_identity: Fp::from(1001),
    };
    let public = original.public_inputs();
    let changed_authority = NullifierCircuit {
        spend_secret: Fp::from(778),
        note_identity: original.note_identity,
    };
    let prover = MockProver::run(NULLIFIER_K, &changed_authority, vec![public])
        .expect("nullifier mismatch prover");
    assert!(prover.verify().is_err());

    // Same authority, different notes: nullifiers must remain note-bound.
    let secret = Fp::from(777);
    assert_eq!(authority_tag(secret), authority_tag(secret));
    assert_ne!(
        nullifier(secret, Fp::from(1001)),
        nullifier(secret, Fp::from(1002))
    );

    // Membership/root sensitivity: changing the circuit-native leaf changes
    // the Poseidon root and cannot satisfy the original public anchor.
    let siblings = [Fp::from(201), Fp::from(202), Fp::from(203), Fp::from(204)];
    let directions = [false, true, false, true];
    let original_leaf = Fp::from(101);
    let changed_leaf = Fp::from(102);
    let original_root = merkle_root(original_leaf, siblings, directions);
    let changed_root = merkle_root(changed_leaf, siblings, directions);
    assert_ne!(original_root, changed_root);

    let changed = AnchorCircuit {
        leaf: changed_leaf,
        siblings,
        directions,
    };
    let prover = MockProver::run(ANCHOR_K, &changed, vec![vec![original_root]])
        .expect("anchor mutation prover");
    assert!(prover.verify().is_err());

    assert_ne!(oracle.phase7_tree_hash, oracle.phase8_tree_hash);
}

#[test]
fn bridge_does_not_claim_hash_byte_compatibility() {
    let oracle = oracle();
    assert_eq!(
        oracle.phase7_tree_hash,
        "domain-separated-sha256-placeholder"
    );
    assert_eq!(oracle.phase8_tree_hash, "halo2-poseidon-p128pow5t3");
    assert!(!oracle.properties.root_byte_compatibility_claimed);
}
