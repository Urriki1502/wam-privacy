//! Security regression: protocol domain separators are fixed circuit constants.
//!
//! This source-shape regression complements the real-proof and MockProver suites.
//! A green test here alone is not proof of constraint-system soundness.

#[test]
fn protocol_domains_are_fixed_in_both_bundle_circuits() {
    let hardened = include_str!("../src/hardened_bundle.rs");
    let legacy_bundle = include_str!("../src/bundle_action.rs");

    for (name, source) in [("10D hardened", hardened), ("10B bundle", legacy_bundle)] {
        assert_eq!(
            source.matches("assign_advice_from_constant(").count(),
            4,
            "{name}: expected the note domain in both input/output paths and both input authority/nullifier domains to be bound to fixed columns"
        );

        for domain in ["NOTE_DOMAIN", "AUTHORITY_DOMAIN", "NULLIFIER_DOMAIN"] {
            let unbound = format!("Value::known(Fp::from({domain}))");
            assert!(
                !source.contains(&unbound),
                "{name}: unbound witness assignment for {domain}"
            );
        }
    }
}
