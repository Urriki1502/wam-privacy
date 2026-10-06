use halo2_proofs::dev::MockProver;
use wam_privacy_halo2_prototype::{BalanceCircuit, MAX_WAM_ATOMS};

const K: u32 = 11;

fn assert_pass(circuit: BalanceCircuit) {
    let prover = MockProver::run(K, &circuit, vec![]).expect("mock prover should build");
    prover.assert_satisfied();
}

fn assert_fail(circuit: BalanceCircuit) {
    let prover = MockProver::run(K, &circuit, vec![]).expect("mock prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn shield_only_balance_passes() {
    assert_pass(BalanceCircuit {
        spent: 0,
        transparent_in: 100_000,
        created: 99_000,
        transparent_out: 0,
        fee: 1_000,
    });
}

#[test]
fn private_transfer_and_unshield_balance_passes() {
    assert_pass(BalanceCircuit {
        spent: 100_000,
        transparent_in: 0,
        created: 74_000,
        transparent_out: 25_000,
        fee: 1_000,
    });
}

#[test]
fn mixed_balance_passes() {
    let circuit = BalanceCircuit {
        spent: 50_000,
        transparent_in: 20_000,
        created: 60_000,
        transparent_out: 9_000,
        fee: 1_000,
    };
    assert_eq!(circuit.lhs(), circuit.rhs());
    assert_pass(circuit);
}

#[test]
fn exact_wam_cap_is_accepted() {
    assert_pass(BalanceCircuit {
        spent: MAX_WAM_ATOMS,
        transparent_in: 0,
        created: MAX_WAM_ATOMS,
        transparent_out: 0,
        fee: 0,
    });
}

#[test]
fn one_atom_over_wam_cap_is_rejected_even_when_balanced() {
    assert_fail(BalanceCircuit {
        spent: MAX_WAM_ATOMS + 1,
        transparent_in: 0,
        created: MAX_WAM_ATOMS + 1,
        transparent_out: 0,
        fee: 0,
    });
}

#[test]
fn u64_max_is_rejected_by_monetary_cap() {
    assert_fail(BalanceCircuit {
        spent: u64::MAX,
        transparent_in: 0,
        created: u64::MAX,
        transparent_out: 0,
        fee: 0,
    });
}

#[test]
fn inflation_attempt_is_unsatisfied() {
    assert_fail(BalanceCircuit {
        spent: 100_000,
        transparent_in: 0,
        created: 100_001,
        transparent_out: 0,
        fee: 0,
    });
}

#[test]
fn hidden_fee_mismatch_is_unsatisfied() {
    assert_fail(BalanceCircuit {
        spent: 100_000,
        transparent_in: 0,
        created: 99_500,
        transparent_out: 0,
        fee: 400,
    });
}
