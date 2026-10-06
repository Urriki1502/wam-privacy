# Phase 8 — Isolated ZK Prototype

## Stage A — Balance circuit

The first Halo2 prototype encoded:

```
spent + transparent_in
=
created + transparent_out + fee
```

Stage A established that the value-conservation equation could be expressed and negative-tested with Halo2's `MockProver`.

Status: **PASS (prototype integration)**.

## Stage B — In-circuit 64-bit amount ranges

Each amount is constrained by a 64-step little-endian decomposition:

```
acc_i = bit_i + 2 * acc_(i+1)
bit_i * (bit_i - 1) = 0
acc_64 = 0
```

The original balance witness cell is equality-constrained to `acc_0`.

Status: **PASS (internal circuit tests)**.

## Stage B2 — Exact WAM monetary cap

The circuit now additionally constrains every amount witness to:

```
0 <= amount <= 22,000,000 * 100,000,000 atoms
```

For each amount it witnesses a non-negative 64-bit `slack` and enforces:

```
amount + slack = MAX_WAM_ATOMS
```

Both `amount` and `slack` are independently range-constrained inside the circuit.

This prevents a field element larger than WAM's monetary domain from passing merely because it is representable as a 64-bit integer.

Boundary tests include:

- exactly `MAX_WAM_ATOMS` — accepted;
- `MAX_WAM_ATOMS + 1` — rejected;
- `u64::MAX` — rejected.

## Planned Phase 8 stages

### Stage C — Commitment-tree anchor

Bind a spent note witness to a commitment-tree anchor derived from Phase 7 semantics.

### Stage D — Nullifier relation

Prove the modeled spend-authority/nullifier relation without exposing the secret authority.

### Stage E — Real proof generation / verification

Move beyond `MockProver` to actual Halo2 proof creation and verification in isolated CI.

### Stage F — Differential bridge

Cross-check accepted/rejected transitions between:

- Phase 7 Python state model;
- Phase 8 Halo2 circuit fixtures.

## Status

`PHASE 8-B2 — IN PROGRESS`

No production, anonymity, audit, or mainnet claim is implied.
