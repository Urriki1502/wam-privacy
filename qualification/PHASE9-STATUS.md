# Phase 9 Status

**Scope:** isolated Halo2 shielded-action composition research.

| Stage | Status | Evidence |
| --- | --- | --- |
| 9A — integrated anchor/nullifier composition | PASS (internal engineering) | one private note-identity cell is reused and constrained across Merkle membership and nullifier derivation; negative tests + real proof verification |
| 9B — in-circuit note commitment derivation | PASS (internal engineering) | private value/recipient/authority/rho/rseed derive the exact anchored + nullified identity; cap/nonzero constraints + real proof |
| 9C — integrated value/action relation | **PASS (internal engineering)** | one input note, one output note and explicit fee share the same constrained value cells; MockProver negatives + real Halo2 proof + five-public-instance tamper rejection |

## Phase 9C invariants

- input value is used by both the input note commitment and conservation gate;
- output value is used by both the output note commitment and conservation gate;
- input note identity is used by both Merkle anchoring and nullifier derivation;
- output note commitment is public and bound to all output note fields;
- fee is public and participates in the exact conservation equation;
- shielded input/output values are non-zero;
- input/output/fee are 64-bit and capped at the exact WAM monetary maximum;
- changing any private linked witness invalidates the original public relation;
- changing any public root, authority tag, nullifier, output commitment or fee invalidates the real proof.

## Qualification evidence

Phase 9C PR qualification completed with all repository workflows successful.

Key workflow evidence:

- Phase 9C integrated value action: run `37559236742` — **PASS**;
- Phase 8 isolated Halo2 suite after CI-scope correction: run `37559236698` — **PASS**;
- Phase 9A integrated shielded action: **PASS**;
- Phase 9B in-circuit note commitment: **PASS**;
- Phase 1–7 regression workflows: **PASS**.

The prior Phase 8 cancellation was a CI-scope/timeout issue: the Phase 8 workflow used `cargo test --all-targets`, which unintentionally executed later Phase 9 real-proof tests and exceeded its 20-minute timeout. Phase 8 now executes only its own Phase 8 test targets; Phase 9A/B/C remain independently qualified by their dedicated workflows.

## Current claim

`PHASE 9C INTERNAL VALUE-ACTION PASS — PHASE 9 RESEARCH STACK QUALIFIED THROUGH 9C`

No production, audit, consensus, anonymity, or mainnet claim is implied.
