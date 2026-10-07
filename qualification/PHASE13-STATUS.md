# Phase 13 Status

**Scope:** isolated WAM Core shielded verifier integration.

| Stage | Status | Evidence |
| --- | --- | --- |
| 13A — Rust/C verifier ABI | **PASS (internal engineering)** | run `37587354356`; real Phase 10D proof verified through C ABI; static/shared library + exported symbols PASS |
| 13B — WAM Core regtest-only verifier hook | UNDER QUALIFICATION | generated-Core patch/build/RPC workflow pending |
| 13C — atomic shielded state / reorg integration | PENDING | requires 13B PASS |
| 13D — resource/DoS qualification | PENDING | requires Core verifier integration |

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

## Phase 13A qualification

PR #34 completed with all 20 repository workflows successful.

Dedicated Phase 13A evidence:

- format: PASS;
- clippy: PASS;
- C header compile: PASS;
- real hardened proof through C ABI: PASS;
- static/shared verifier library build: PASS;
- exported ABI symbol checks: PASS;
- run: `37587354356`;
- merge commit: `d30e1b8f45cd3d062a26541c6f711a7562093880`.

## Current claim

`PHASE 13A PASS — PHASE 13B GENERATED-CORE REGTEST HOOK UNDER QUALIFICATION`

No WAM Core consensus source was modified by Phase 13A. Phase 13B remains regtest-only and disabled from normal Core builds.
