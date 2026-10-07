# Phase 9 Status

**Scope:** isolated Halo2 shielded-action composition research.

| Stage | Status | Evidence |
| --- | --- | --- |
| 9A — integrated anchor/nullifier composition | PASS (internal engineering) | one private note-identity cell is reused and constrained across Merkle membership and nullifier derivation; negative tests + real proof verification |
| 9B — in-circuit note commitment derivation | PASS (internal engineering) | private value/recipient/authority/rho/rseed derive the exact anchored + nullified identity; cap/nonzero constraints + real proof |
| 9C — integrated value/action relation | UNDER QUALIFICATION | one input note, one output note and explicit fee are composed with exact value conservation in the same Halo2 relation |

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

## Current claim

`PHASE 9C UNDER QUALIFICATION — PHASE 9 IN PROGRESS`

No production, audit, consensus, anonymity, or mainnet claim is implied.
