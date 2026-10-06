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

Stage B removes reliance on host-side `u64` typing as the only amount bound.

Each amount is copied into an in-circuit little-endian decomposition satisfying:

```
acc_i = bit_i + 2 * acc_(i+1)
bit_i * (bit_i - 1) = 0
acc_64 = 0
```

The original balance witness cell is equality-constrained to `acc_0`.

This establishes that every amount used by the conservation equation is a 64-bit field value inside the circuit.

### Remaining monetary-range work

WAM's exact monetary cap is lower than `2^64 - 1`. Stage B therefore blocks field-wraparound ambiguity but does **not** yet prove:

```
amount <= 22,000,000 * 100,000,000
```

An exact monetary-cap comparator remains required before any production-oriented claim.

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

`PHASE 8-B — IN PROGRESS`

No production, anonymity, audit, or mainnet claim is implied.
