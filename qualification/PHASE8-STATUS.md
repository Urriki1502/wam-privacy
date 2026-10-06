# Phase 8 Status

**Scope:** isolated Halo2 research prototype only.

| Stage | Status | Evidence |
| --- | --- | --- |
| 8A — value conservation | PASS (internal engineering) | Halo2 MockProver positive/negative balance tests |
| 8B — 64-bit ranges | PASS (internal engineering) | boolean decomposition and termination constraints |
| 8B2 — exact WAM monetary cap | PASS (internal engineering) | cap, cap+1 and u64::MAX boundary tests |
| 8C — commitment-tree anchor | PASS (internal engineering) | Poseidon path/root positive and tamper-negative tests |
| 8D — nullifier relation | PASS (internal engineering) | private authority/note witnesses bound to public Poseidon tag/nullifier; tamper-negative tests |
| 8E — real proof generation/verification | PASS (internal engineering) | actual Halo2 create_proof/verify_proof for balance, anchor and nullifier circuits |
| 8F — Phase7/Phase8 differential bridge | PASS (internal engineering) | executable Phase 7 oracle regenerated in CI and consumed by Halo2 semantic bridge tests |

## Phase 8C security properties

- authentication siblings remain private witnesses;
- path direction remains private and boolean-constrained;
- the final tree root is a public instance;
- changing the root, a sibling, or a path direction invalidates the witness;
- hashing uses the upstream Halo2 Poseidon gadget rather than a custom WAM hash.

## Phase 8D security properties

- spend authority remains a private witness;
- note identity remains a private witness;
- changing either private witness invalidates the original public relation;
- nullifiers are note-bound so one authority does not map all notes to one identifier;
- domain constants are constrained in-circuit;
- hashing uses the upstream Halo2 Poseidon gadget.

### Composition boundary

Stage 8D does not yet prove that its private note identity is the exact leaf proven by Stage 8C. That cell-level composition remains a later integration requirement and is intentionally not claimed here.

## Phase 8E proof evidence

The CI suite exercises actual Halo2 proof creation and verification, not only `MockProver`.

Verified behaviors:

- balance circuit proof creation and verification succeeds;
- anchor circuit proof creation and verification succeeds;
- anchor proof fails against a modified public root;
- nullifier circuit proof creation and verification succeeds;
- nullifier proof fails against a modified public nullifier.

All proving parameters and proving/verifying keys are generated ephemerally inside the isolated test process.

## Phase 8F differential evidence

Phase 8F adds a cross-language semantic bridge:

1. Python executes the actual Phase 7 shielded model and regenerates an oracle.
2. CI requires the regenerated oracle to exactly match the committed fixture.
3. Rust/Halo2 consumes that same fixture.
4. Halo2 acceptance/rejection is compared against Phase 7 for shared balance and WAM monetary-cap semantics.
5. Relational properties are cross-checked for authority mismatch, note-bound nullifiers and commitment/root mutation sensitivity.

The bridge deliberately compares **semantics**, not hash bytes.

## Important model boundary

Phase 7 uses domain-separated SHA-256 solely for deterministic executable-model vectors.

Phase 8C uses a Poseidon circuit-native tree.

These roots are intentionally **not claimed to be byte-compatible**. A future protocol decision must define one canonical production tree/hash construction before any cross-layer or consensus integration claim.

## Current claim

`PHASE 8F INTERNAL DIFFERENTIAL PASS — PLANNED PHASE 8 QUALIFICATION STAGES COMPLETE`

This is not an audit, anonymity guarantee, production-readiness statement, consensus specification, or mainnet activation proposal.
