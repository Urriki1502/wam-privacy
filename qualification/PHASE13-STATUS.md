# Phase 13 Status

**Scope:** isolated WAM Core shielded verifier and state integration.

| Stage | Status | Evidence |
| --- | --- | --- |
| 13A — Rust/C verifier ABI | **PASS (internal engineering)** | run `37587354356`; real Phase 10D proof verified through C ABI; static/shared library + exported symbols PASS |
| 13B — generated WAM Core regtest-only verifier hook | **PASS (internal engineering)** | run `37597535877`; generated-Core build/link/RPC qualification PASS; merge `a2bd4cd7bb21679ee0e64a174046c1b7b0b5ff09` |
| 13C — atomic shielded state / reorg integration | **PASS (internal engineering)** | run `37600960274`; atomic failure, proof-bound metadata, disconnect and 300-block rollback/replay PASS |
| 13D — resource / DoS qualification | **UNDER QUALIFICATION** | parser bounds, block transition cap and non-blocking verifier concurrency gate |

## Phase 13A invariants

- only regtest is accepted;
- the Core-facing caller supplies transaction digest and transparent value context;
- the envelope must match the pinned hardened circuit/VK;
- invalid proof/context/encoding fails without state mutation;
- Rust panic cannot unwind into C++;
- verifier material is initialized once per handle rather than regenerated per proof;
- constructor failure nulls the caller output handle;
- ABI error values are stable and non-secret;
- C header compiles independently;
- expected verifier symbols are exported from the shared library.

## Phase 13B invariants

- normal generated-Core builds remain verifier-disabled;
- the experimental RPC exists only with the explicit compile/link gates;
- runtime is regtest-only;
- the RPC is read-only;
- no validation, mempool, coins, or persistent chainstate mutation is introduced;
- malformed proof/context/value inputs fail closed;
- exact WAM Core revision is pinned for qualification.

## Phase 13C invariants

- nullifiers and output commitments are extracted only from a verified Phase 10D proof;
- block application is all-or-nothing;
- duplicate nullifiers and commitments fail closed;
- every transition is bound to the current anchor;
- height and parent linkage are exact;
- pool arithmetic is checked and WAM-cap bounded;
- disconnect restores prior anchor, pool, nullifier and commitment state;
- deep rollback and replacement replay are deterministic.

## Phase 13D invariants

- oversized proof declarations fail before payload processing;
- malformed/truncated envelopes fail closed;
- a block cannot exceed the explicit shielded-transition cap;
- exceeding the block transition cap fails before state mutation;
- only one expensive verifier call may execute through the Core wrapper at a time;
- a concurrent verification attempt returns `BUSY` without entering Halo2;
- the resource gates do not relax the regtest-only or compile-time experimental boundaries.

## Current claim

`PHASE 13A/13B/13C PASS — PHASE 13D RESOURCE/DoS QUALIFICATION IN PROGRESS`

No WAM Core consensus activation, shielded mempool acceptance, persistent production
chainstate, testnet, or mainnet claim is implied.
