# Phase 8 Status

**Scope:** isolated Halo2 research prototype only.

| Stage | Status | Evidence |
| --- | --- | --- |
| 8A — value conservation | PASS (internal engineering) | Halo2 MockProver positive/negative balance tests |
| 8B — 64-bit ranges | PASS (internal engineering) | boolean decomposition and termination constraints |
| 8B2 — exact WAM monetary cap | PASS (internal engineering) | cap, cap+1 and u64::MAX boundary tests |
| 8C — commitment-tree anchor | PASS (internal engineering) | Poseidon path/root positive and tamper-negative tests |
| 8D — nullifier relation | PENDING | not implemented |
| 8E — real proof generation/verification | PENDING | not implemented |
| 8F — Phase7/Phase8 differential bridge | PENDING | not implemented |

## Phase 8C security properties

- authentication siblings remain private witnesses;
- path direction remains private and boolean-constrained;
- the final tree root is a public instance;
- changing the root, a sibling, or a path direction invalidates the witness;
- hashing uses the upstream Halo2 Poseidon gadget rather than a custom WAM hash.

## Important model boundary

Phase 7 uses domain-separated SHA-256 solely for deterministic executable-model vectors.

Phase 8C uses a Poseidon circuit-native tree.

These roots are intentionally **not claimed to be byte-compatible**. A future protocol decision must define one canonical production tree/hash construction before any cross-layer or consensus integration claim.

## Current claim

`PHASE 8C INTERNAL ENGINEERING PASS — PHASE 8 REMAINS IN PROGRESS`

This is not an audit, anonymity guarantee, production-readiness statement, or mainnet activation proposal.
