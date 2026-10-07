# Phase 13 Status

**Scope:** isolated WAM Core shielded verifier integration.

| Stage | Status | Evidence |
| --- | --- | --- |
| 13A — Rust/C verifier ABI | UNDER QUALIFICATION | dedicated Phase 13A workflow pending |
| 13B — WAM Core regtest-only verifier hook | PENDING | requires 13A PASS |
| 13C — atomic shielded state / reorg integration | PENDING | requires 13B PASS |
| 13D — resource/DoS qualification | PENDING | requires Core verifier integration |

## Phase 13A invariants

- only regtest is accepted;
- the Core-facing caller supplies transaction digest and transparent value context;
- the envelope must match the pinned hardened circuit/VK;
- invalid proof/context/encoding fails without state mutation;
- Rust panic cannot unwind into C++;
- verifier material is initialized once per handle rather than regenerated per proof;
- ABI error values are stable and non-secret.

## Current claim

`PHASE 13A CORE VERIFIER FFI — QUALIFICATION PENDING`

No WAM Core consensus source is modified by Phase 13A.
