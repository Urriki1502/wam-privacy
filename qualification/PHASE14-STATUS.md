# Phase 14 Status

**Scope:** hardening and reproducible release qualification before external review.

| Stage | Status | Evidence |
| --- | --- | --- |
| 14A — reproducible dependency / release identity | **PASS (internal engineering)** | run `37610249058`; locked dependency graph, same-runner double-build artifact hashes and deterministic VK identity PASS |
| 14B — parser/verifier fuzzing + adversarial corpus | **PASS (internal engineering)** | run `37615083459`; 100k executions/target + real-proof adversarial corpus + full regressions PASS |
| 14C — proving/verifying performance + memory/resource benchmarks | **PASS (internal engineering)** | run `37620295551`; proof/verify/RSS/size profile within explicit ceilings |
| 14D — upgrade/migration/static-review + final evidence ledger | **PASS (internal engineering)** | run `37623838673`; version/migration rejection + static boundary inventory + deterministic final ledger PASS |

## Current claim

`PHASE 14 INTERNAL HARDENING COMPLETE — READY FOR PHASE 15 EXTERNAL REVIEW / TESTNET QUALIFICATION`

This is an internal engineering result. It is not an external audit, production release, mainnet activation, or anonymity guarantee.

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

## Phase 14B evidence

- qualification head: `9798d4aa4d1367f91ce3eaea7d30d14d8133a76c`;
- workflow run: `37615083459`;
- parser fuzz target: **100,000 executions PASS**;
- verifier-precheck fuzz target: **100,000 executions PASS**;
- deterministic corpus + SHA-256 manifest: **PASS**;
- real Phase 10D proof adversarial mutations: **PASS / fail-closed**;
- Phase 1–14A regression workflows on the same head: **PASS**.

## Phase 14C evidence

- qualification head: `2f57104d152535a7dda30cdbdc55bab367e7771e`;
- workflow run: `37620295551`;
- artifact digest: `sha256:37ed1953b9e7fd120cc287311d245408ad309fb76586e2c95fe6a242dbe54595`;
- setup / VK+PK: **50,637 ms**;
- proof generation: **17,369 ms**;
- verification average (3 rounds): **305 ms**;
- verification maximum: **306 ms**;
- proof size: **5,728 bytes**;
- encoded envelope: **6,061 bytes**;
- peak RSS: **1,498,028 KiB**;
- qualification ceilings: **PASS with zero violations**;
- Phase 1–14B regression workflows on the same head: **PASS**.

## Phase 14D evidence

- qualification head: `7976d0bc56542d5a2501aade924ee17846ff4e52`;
- merged qualification baseline: `00f8065c4f7b48fec01e4d97626ecbf2cc125852`;
- workflow run: `37623838673`;
- artifact: `phase14d-final-hardening`;
- artifact digest: `sha256:a41c7bb7eaa04e370acfdedc9f5c33d0b426c4c8051f6ac0efc610cfc42bdaec`;
- legacy v1 / hardened v2 cross-decoding rejection: **PASS**;
- unknown/future format and circuit rejection: **PASS**;
- protocol/network context separation: **PASS**;
- production-facing static boundary inventory: **PASS**;
- unsafe-code inventory: **PASS**;
- panic containment / regtest gating / experimental Core gate / non-blocking verifier concurrency checks: **PASS**;
- final deterministic evidence ledger build: **PASS**;
- Phase 1–14C regression workflows on the same head: **PASS**.

## Phase 14 completion boundary

All project-owned internal hardening gates are closed.

The remaining work begins at Phase 15 and deliberately depends on external review and extended testnet evidence before any maintainer activation decision.
