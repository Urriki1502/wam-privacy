# Phase 14 Status

**Scope:** hardening and reproducible release qualification before external review.

| Stage | Status | Evidence |
| --- | --- | --- |
| 14A — reproducible dependency / release identity | **PASS (internal engineering)** | run `37610249058`; locked dependency graph, same-runner double-build artifact hashes and deterministic VK identity PASS |
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

`PHASE 14A REPRODUCIBLE RELEASE IDENTITY — INTERNAL ENGINEERING PASS`

No external-audit, production-release, consensus-activation or mainnet claim is implied.


## Phase 14A evidence

- qualification head: `ac9550e9e966c2e22cbadb96bb0ef57c4d14b2fa`;
- workflow run: `37610249058`;
- evidence artifact digest: `sha256:6f03aff679d3e9a104b8e9bc0c6570436eaafd288bdc5f5fdae4a6369d09cf49`;
- Cargo.lock SHA-256: `4e3824e9bacfa07b64edf390f16e8decf802e4684c02732440dab0b62b7b8948`;
- Cargo.toml SHA-256: `82881664be247998def48e26ad4c7a1a23d638f9706668dbbed17191515947b9`;
- rust-toolchain.toml SHA-256: `6a3177dca3783745b00765ea571974808dad2644947fc0a8df5927048edf13a5`;
- protocol version: `1`;
- circuit id: `2564`;
- verifier k: `15`;
- VK id: `de8ae5b7a5a149c11587f6b0e14f61954aea404461642a6ad1eb18b3a5b1700a`;
- static library SHA-256: `efcedac97c0759908aa165611dd1a8cf23db1013e527c05ee44420d9391bebbe`;
- shared library SHA-256: `8716395a55b431b8b92ec2abe23f8096a251375f741b26dbcaee0756aa1d31df`;
- same-runner double-build match: **true**.
