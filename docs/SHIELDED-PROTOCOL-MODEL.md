# Phase 7 — Shielded Protocol State Model

**Status:** Research / executable specification only.

This phase does not implement zero-knowledge proofs, transaction confidentiality, or a production shielded pool. It models the state-transition rules that any future proof system would need to enforce.

## Why state semantics come first

A shielded protocol can hide transaction details and still be unsafe if its state machine permits:

- the same note to be spent twice;
- the same note to generate multiple nullifiers through unrelated spend keys;
- notes that never existed to be spent;
- duplicate commitments;
- shielded value to be created without transparent input;
- more transparent value to leave than the pool contains;
- ambiguous protocol-version interpretation;
- viewing authority to silently become spending authority.

Phase 7 therefore makes those rules executable before any Halo 2 prototype is attempted.

## Modeled objects

### Note

The model carries:

- value;
- recipient/view tag;
- spend-key tag;
- rho;
- random seed;
- protocol version.

The view tag and spend-key tag are deliberately distinct model domains. A valid viewing key can recognize a modeled note but cannot be used as its spend/nullifier authority.

The value is intentionally visible in this model. Confidential values belong to Phase 8 proof-system research.

### Note commitment

A deterministic, domain-separated SHA-256 placeholder is used only for model vectors.

It is **not** a proposed production commitment scheme.

### Nullifier

A deterministic, domain-separated SHA-256 placeholder models one-time spend identity. Before a nullifier is derived, the supplied nullifier key must match the note's committed spend-key tag.

It is **not** a proposed production nullifier construction.

### Commitment root

The model maintains an append-only commitment list and computes a deterministic placeholder binary-Merkle root. This gives future proof research an explicit state anchor.

The SHA-256 Merkle construction is only a model and is not a proposed production tree/hash primitive.

### Shielded state

State contains:

- append-only note commitments;
- spent nullifiers;
- total transparent value currently accounted inside the modeled shielded pool;
- deterministic commitment root;
- protocol version.

## Formal value-conservation rule

For every accepted transition:

```
sum(spent shielded notes)
+ transparent_in
=
sum(new shielded notes)
+ transparent_out
+ fee
```

In addition:

```
new_pool_balance
=
old_pool_balance
+ transparent_in
- transparent_out
```

and the pool balance may never become negative.

These are separate invariants. Both must hold.

## Mandatory invariants

### SHIELD-INV-01 — Existing-note membership

Every spent note commitment must already exist in the state.

### SHIELD-INV-02 — View/spend separation

A viewing key may recognize its note but is not sufficient to derive a valid nullifier unless it independently equals the bound spend authority.

### SHIELD-INV-03 — Spend-authority binding

The spend/nullifier key must match the authority tag committed into the note.

### SHIELD-INV-04 — Nullifier uniqueness

A valid nullifier may be accepted once and only once.

### SHIELD-INV-05 — Value conservation

No transition may create shielded or transparent value outside the conservation equation.

### SHIELD-INV-06 — Pool solvency

Unshielding cannot drive the modeled shielded pool below zero.

### SHIELD-INV-07 — Commitment uniqueness

A newly created note commitment must not duplicate an existing or same-transition commitment.

### SHIELD-INV-08 — State anchoring

The ordered commitment set deterministically maps to one model root.

### SHIELD-INV-09 — Explicit versioning

Unknown note/state/transition versions fail closed.

### SHIELD-INV-10 — Deterministic vectors

View tags, spend-key tags, model commitments, model nullifiers and roots are fixed so accidental semantic drift is visible in CI.

## Relationship to Zcash Orchard / Halo 2

Orchard and Halo 2 remain research references for later proof-system design, especially:

- note commitments;
- nullifiers;
- incoming viewing capabilities;
- action/value balance;
- commitment-tree anchors;
- proof verification;
- upgrade discipline.

WAM does not claim Orchard compatibility and does not copy Orchard consensus encoding in this phase.

## Explicit non-claims

A Phase 7 PASS does not mean:

- amounts are confidential;
- recipients are hidden;
- the placeholder hashes are cryptographically suitable commitment/nullifier/tree primitives;
- a zero-knowledge circuit exists;
- a proving system has been audited;
- WAM Core can activate a shielded pool.

It means only that the executable state model satisfies the tested invariants.
