# Phase 9 Status

**Scope:** isolated Halo2 shielded-action composition research.

| Stage | Status | Evidence |
| --- | --- | --- |
| 9A — integrated anchor/nullifier composition | PASS (internal engineering) | one private note-identity cell is reused and constrained across Merkle membership and nullifier derivation; negative tests + real proof verification |
| 9B — in-circuit note commitment derivation | PENDING | complete private note fields are not yet reduced to the anchored note identity |
| 9C — integrated value/action relation | PENDING | value conservation is not yet composed into the same action circuit |

## Phase 9A invariants

- note identity is assigned once;
- the same note-identity cell is the Merkle leaf and nullifier input;
- spend authority remains private;
- authentication path remains private;
- root, authority tag and nullifier are public instances;
- changing any linked private witness invalidates the original public relation;
- changing any public output invalidates the real proof.

## Current claim

`PHASE 9A INTERNAL COMPOSITION PASS — PHASE 9 IN PROGRESS`

No production, audit, consensus, or mainnet claim is implied.
