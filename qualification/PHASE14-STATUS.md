# Phase 14 Status

**Scope:** hardening and reproducible release qualification before external review.

| Stage | Status | Evidence |
| --- | --- | --- |
| 14A — reproducible dependency / release identity | **PASS (internal engineering)** | run 37610493266; artifact digest sha256:6f03aff679d3e9a104b8e9bc0c6570436eaafd288bdc5f5fdae4a6369d09cf49 |
| 14B — parser/verifier fuzzing + adversarial corpus | **UNDER QUALIFICATION** | coverage-guided parser/precheck fuzzing + real-proof adversarial corpus |
| 14C — proving/verifying performance + memory/resource benchmarks | PENDING | requires 14A PASS |
| 14D — upgrade/migration/static-review + final evidence ledger | PENDING | requires 14B/14C PASS |

## Phase 14A result

- Rust toolchain explicitly pinned;
- committed Cargo dependency lock consumed with --locked;
- two clean release builds produced identical static/shared verifier-library hashes;
- protocol version, circuit id, verifier K and VK identity matched across both build paths;
- machine-readable release-identity evidence archived.

## Phase 14B invariants

- arbitrary envelope bytes cannot panic the parser;
- any accepted decode canonicalizes deterministically;
- verifier precheck cannot accept wrong VK/context/transparent balance;
- real proof mutations fail closed;
- fuzz input length and resource use are bounded;
- corpus/evidence hashes are archived.

## Current claim

PHASE 14A INTERNAL ENGINEERING PASS — PHASE 14B FUZZ QUALIFICATION IN PROGRESS

No external-audit, production-release, consensus-activation or mainnet claim is implied.
