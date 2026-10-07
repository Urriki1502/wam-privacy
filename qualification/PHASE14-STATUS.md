# Phase 14 Status

**Scope:** hardening and reproducible release qualification before external review.

| Stage | Status | Evidence |
| --- | --- | --- |
| 14A — reproducible dependency / release identity | **PASS (internal engineering)** | run `37610249058`; locked dependency graph, same-runner double-build artifact hashes and deterministic VK identity PASS |
| 14B — parser/verifier fuzzing + adversarial corpus | **PASS (internal engineering)** | run `37615083459`; 100k executions/target + real-proof adversarial corpus + full regressions PASS |
| 14C — proving/verifying performance + memory/resource benchmarks | **UNDER QUALIFICATION** | dedicated fixed-runner proof/verify/RSS/size benchmark |
| 14D — upgrade/migration/static-review + final evidence ledger | PENDING | requires 14B/14C PASS |

## Phase 14A invariants

- Rust toolchain is explicitly pinned;
- dependency resolution is committed and consumed with `--locked`;
- release identity binds the exact source revision and dependency lock;
- circuit id / protocol version / VK identity are reproducible;
- independently repeated release builds on the same qualification runner produce identical verifier library hashes;
- qualification evidence records hashes rather than relying on filenames or mutable tags.

## Current claim

`PHASE 14B INTERNAL ENGINEERING PASS — PHASE 14C PERFORMANCE QUALIFICATION IN PROGRESS`

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

## Phase 14B invariants

- arbitrary envelope bytes cannot panic the parser;
- any accepted decode canonicalizes deterministically;
- verifier precheck cannot accept wrong VK/context/transparent balance;
- real proof mutations fail closed;
- fuzz input length and resource use are bounded;
- corpus/evidence hashes are archived.


## Phase 14B evidence

- qualification head: `9798d4aa4d1367f91ce3eaea7d30d14d8133a76c`;
- workflow run: `37615083459`;
- parser fuzz target: **100,000 executions PASS**;
- verifier-precheck fuzz target: **100,000 executions PASS**;
- deterministic corpus + SHA-256 manifest: **PASS**;
- real Phase 10D proof adversarial mutations: **PASS / fail-closed**;
- Phase 1–14A regression workflows on the same head: **PASS**.

## Phase 14C invariants

- benchmark uses the pinned Phase 10D hardened 2×2 circuit;
- proof generation and verification are measured separately;
- proof and encoded-envelope sizes are recorded;
- peak RSS is measured on the already-built benchmark process, not the compiler;
- benchmark runner/toolchain identity is archived;
- broad fail-closed ceilings catch pathological performance/resource regressions without pretending CI timing is a production SLA.
