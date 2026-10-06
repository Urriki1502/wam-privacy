# Phase 9 Status

**Scope:** isolated Halo2 shielded-action composition research.

| Stage | Status | Evidence |
| --- | --- | --- |
| 9A — integrated anchor/nullifier composition | PASS (internal engineering) | one private note-identity cell is reused and constrained across Merkle membership and nullifier derivation; negative tests + real proof verification |
| 9B — in-circuit note commitment derivation | PASS (internal engineering) | private value/recipient/authority/rho/rseed derive the exact anchored + nullified identity; cap/nonzero constraints + real proof |
| 9C — integrated value/action relation | PENDING | value conservation is not yet composed into the same action circuit |

## Phase 9A invariants

- note identity is assigned once;
- the same note-identity cell is the Merkle leaf and nullifier input;
- spend authority remains private;
- authentication path remains private;
- root, authority tag and nullifier are public instances;
- changing any linked private witness invalidates the original public relation;
- changing any public output invalidates the real proof.

## Phase 9B invariants

- note identity is no longer supplied as an unconstrained precomputed witness;
- private value, recipient tag, spend authority tag, rho and rseed are Poseidon-bound into the note identity;
- the derived note-identity cell is reused directly as the Merkle leaf and nullifier input;
- note value is constrained to be non-zero, 64-bit and no greater than the exact WAM monetary cap;
- changing any private note field invalidates the original public relation;
- exact cap is accepted and cap + 1 is rejected;
- a real Halo2 proof binds root, authority tag and nullifier to the derived note.

## Current claim

`PHASE 9B INTERNAL NOTE-COMMITMENT PASS — PHASE 9 IN PROGRESS`

No production, audit, consensus, or mainnet claim is implied.
