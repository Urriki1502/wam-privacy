use halo2_proofs::dev::MockProver;
use wam_privacy_halo2_prototype::BalanceCircuit;

const K: u32 = 10;

fn assert_pass(circuit: BalanceCircuit) {
    let prover = MockProver::run(K, &circuit, vec![]).expect("mock prover should build");
    prover.assert_satisfied();
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
fn full_u64_witness_is_range_constrained_and_can_balance() {
    assert_pass(BalanceCircuit {
        spent: u64::MAX,
        transparent_in: 0,
        created: u64::MAX - 1,
        transparent_out: 0,
        fee: 1,
    });
}

#[test]
fn inflation_attempt_is_unsatisfied() {
    let circuit = BalanceCircuit {
        spent: 100_000,
        transparent_in: 0,
        created: 100_001,
        transparent_out: 0,
        fee: 0,
    };

    let prover = MockProver::run(K, &circuit, vec![]).expect("mock prover should build");
    assert!(prover.verify().is_err());
}

#[test]
fn hidden_fee_mismatch_is_unsatisfied() {
    let circuit = BalanceCircuit {
        spent: 100_000,
        transparent_in: 0,
        created: 99_500,
        transparent_out: 0,
        fee: 400,
    };

    let prover = MockProver::run(K, &circuit, vec![]).expect("mock prover should build");
    assert!(prover.verify().is_err());
}
