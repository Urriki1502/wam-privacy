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

## Stage C — Commitment-tree anchor

Stage C adds a separate Halo2 `AnchorCircuit` that binds:

- a private field-encoded commitment leaf;
- a private fixed-depth authentication path;
- private boolean direction bits;

to a **public commitment-tree anchor**.

Each tree level constrains child ordering from the private direction bit and computes the parent with the standard Zcash Halo2 Poseidon gadget:

```
parent = Poseidon(left, right)
```

Negative tests reject:

- a wrong public anchor;
- a tampered sibling;
- a tampered direction path.

The circuit supports both left- and right-oriented paths.

The Phase 7 SHA-256 commitment-tree root remains an executable-model placeholder. Stage C deliberately does **not** claim byte compatibility with that placeholder; it establishes a circuit-native membership relation using a reviewed upstream gadget rather than inventing a WAM-specific hash.

Dependencies currently pinned:

- `halo2_proofs = 0.3.5`
- `halo2_gadgets = 0.5.0`

Status: **PASS (internal circuit tests)**.

## Planned Phase 8 stages

### Stage D — Nullifier relation

Prove the modeled spend-authority/nullifier relation without exposing the secret authority.

### Stage E — Real proof generation / verification

Move beyond `MockProver` to actual Halo2 proof creation and verification in isolated CI.

### Stage F — Differential bridge

Cross-check accepted/rejected transitions between:

- Phase 7 Python state model;
- Phase 8 Halo2 circuit fixtures.

## Status

`PHASE 8-C — INTERNAL ENGINEERING PASS / PHASE 8 IN PROGRESS`

No production, anonymity, audit, or mainnet claim is implied.
