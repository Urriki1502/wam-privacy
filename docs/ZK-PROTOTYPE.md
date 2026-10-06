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

## Stage D — Nullifier / spend-authority relation

Stage D adds a separate `NullifierCircuit` with two private witnesses:

- spend authority;
- note identity.

It constrains:

```
authority_tag = Poseidon(AUTHORITY_DOMAIN, spend_secret)

note_key = Poseidon(spend_secret, note_identity)
nullifier = Poseidon(NULLIFIER_DOMAIN, note_key)
```

The spend authority and note identity remain private. The isolated prototype exposes the expected authority tag and nullifier as public instances so the relations can be independently negative-tested.

Tests verify:

- a correct authority/note pair is accepted;
- changing the private spend authority invalidates the original public outputs;
- changing the private note identity invalidates the original nullifier;
- the same authority used with different note identities yields different nullifiers;
- different authorities yield different authority tags and nullifiers;
- swapping the public tag/nullifier positions is rejected.

This is a circuit-native research relation, not a final WAM consensus encoding. The spend authority is currently represented as a Pasta field element and the note identity has not yet been connected to the Stage C anchored leaf in one integrated circuit.

Status: **PASS (internal circuit tests)**.

## Stage E — Real proof generation / verification

Stage E moves beyond `MockProver` and exercises the real Halo2 proving pipeline in isolated CI.

For each current circuit family the test suite generates ephemeral parameters and proving/verifying keys, creates an actual proof, and verifies it:

- value-conservation / amount-domain circuit;
- commitment-tree anchor circuit;
- nullifier / spend-authority circuit.

For public-input circuits, the same proof is also checked against modified public inputs:

- changing the public commitment root causes verification failure;
- changing the public nullifier causes verification failure.

The parameters and keys are ephemeral test artifacts. Stage E does not define production parameter distribution, proving-key custody, verifier integration, or consensus serialization.

Status: **PASS (internal real-proof tests)**.

## Planned Phase 8 stages

### Stage F — Differential bridge

Cross-check accepted/rejected transitions between:

- Phase 7 Python state model;
- Phase 8 Halo2 circuit fixtures.

## Status

`PHASE 8-E — INTERNAL REAL-PROOF PASS / PHASE 8 IN PROGRESS`

No production, anonymity, audit, or mainnet claim is implied.
