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

Every amount witness is constrained to:

```
0 <= amount <= 22,000,000 * 100,000,000 atoms
```

For each amount the circuit witnesses a non-negative 64-bit `slack` and enforces:

```
amount + slack = MAX_WAM_ATOMS
```

Both `amount` and `slack` are independently range-constrained inside the circuit.

Boundary tests include:

- exactly `MAX_WAM_ATOMS` — accepted;
- `MAX_WAM_ATOMS + 1` — rejected;
- `u64::MAX` — rejected.

Status: **PASS (internal circuit tests)**.

## Stage C — Commitment-tree anchor

Stage C adds a separate Halo2 `AnchorCircuit` that binds a private field-encoded commitment leaf, a private fixed-depth authentication path and private boolean direction bits to a **public commitment-tree anchor**.

Each tree level constrains child ordering from the private direction bit and computes:

```
parent = Poseidon(left, right)
```

Negative tests reject a wrong public anchor, a tampered sibling and a tampered direction path.

The Phase 7 SHA-256 commitment-tree root remains an executable-model placeholder. Stage C deliberately does **not** claim byte compatibility with it.

Status: **PASS (internal circuit tests)**.

## Stage D — Nullifier / spend-authority relation

Stage D adds a separate `NullifierCircuit` with private spend authority and private note identity:

```
authority_tag = Poseidon(AUTHORITY_DOMAIN, spend_secret)

note_key = Poseidon(spend_secret, note_identity)
nullifier = Poseidon(NULLIFIER_DOMAIN, note_key)
```

Tests verify authority binding, note binding, nullifier separation and public-input ordering.

The spend authority is currently represented as a Pasta field element and the note identity has not yet been connected to the Stage C anchored leaf in one integrated circuit.

Status: **PASS (internal circuit tests)**.

## Stage E — Real proof generation / verification

Stage E exercises actual Halo2 proving and verification for the balance, anchor and nullifier circuit families. Public-input tampering is negative-tested against produced proofs.

Parameters and proving/verifying keys are ephemeral test artifacts.

Status: **PASS (internal real-proof tests)**.

## Stage F — Phase 7 / Phase 8 semantic differential bridge

Stage F executes the real Phase 7 Python model to generate a deterministic semantic oracle and requires CI to reproduce that oracle exactly.

The Halo2 Rust tests consume the same oracle and cross-check:

- accepted and rejected value-conservation transitions;
- the exact WAM monetary cap;
- authority-mismatch rejection semantics;
- note-bound nullifier separation;
- commitment/root mutation sensitivity.

The bridge explicitly records:

```
comparison_mode = semantic-not-byte-equivalence
```

because Phase 7 uses a domain-separated SHA-256 placeholder tree while Phase 8 uses Halo2 Poseidon. Equal security semantics are tested where the models overlap; byte-equal roots or nullifiers are **not** claimed.

Status: **PASS (internal differential tests)**.

## Remaining research boundary

The planned Phase 8 qualification stages A–F are complete, but the prototype still does not establish:

- one integrated circuit that binds note fields → commitment leaf → anchor → nullifier;
- a canonical production note/commitment encoding;
- production proof serialization or verifier integration;
- consensus nullifier uniqueness;
- note encryption or viewing-key cryptography;
- proving performance targets;
- external cryptographic audit;
- WAM Core or mainnet integration.

## Status

`PHASE 8-F — INTERNAL DIFFERENTIAL PASS / PLANNED PHASE 8 QUALIFICATION STAGES COMPLETE`

No production, anonymity, audit, consensus, or mainnet claim is implied.
