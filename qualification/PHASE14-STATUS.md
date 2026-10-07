# Phase 14 Status

**Scope:** hardening and reproducible release qualification before external review.

| Stage | Status | Evidence |
| --- | --- | --- |
| 14A — reproducible dependency / release identity | **UNDER QUALIFICATION** | lockfile, toolchain, circuit/VK and artifact identity gate |
| 14B — parser/verifier fuzzing + adversarial corpus | PENDING | requires 14A PASS |
| 14C — proving/verifying performance + memory/resource benchmarks | PENDING | requires 14A PASS |
| 14D — upgrade/migration/static-review + final evidence ledger | PENDING | requires 14B/14C PASS |

## Phase 14A invariants

- Rust toolchain is explicitly pinned;
- dependency resolution is committed and consumed with `--locked`;
- release identity binds the exact source revision and dependency lock;
- circuit id / protocol version / VK identity are reproducible;
- independently repeated release builds on the same qualification runner produce identical verifier library hashes;
- qualification evidence records hashes rather than relying on filenames or mutable tags.

## Current claim

`PHASE 14A REPRODUCIBLE RELEASE IDENTITY — QUALIFICATION IN PROGRESS`

No external-audit, production-release, consensus-activation or mainnet claim is implied.
