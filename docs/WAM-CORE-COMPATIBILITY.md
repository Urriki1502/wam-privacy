# WAM Core Compatibility — Phase 1

**Status:** Draft qualification target.

## Locked revisions

| Role | Repository | Revision | Status |
| --- | --- | --- | --- |
| Existing WSP-qualified Core | `wamcoin-core-dev/wam-coin` | `8a3f4fe4f1d804c378f795d4cc281ec5125f75f3` | Previously qualified on regtest |
| Current qualification target | `wamcoin-core-dev/wam-coin` | `260bc468e5adffea7ce68d8f97fac3e27e4c50b2` | Requalification pending |
| Existing WSP implementation | `Urriki1502/wam-silent-payments` | `feat/wsp1-v1.0` | Engineering baseline |

## Core delta

The current Core target is 41 commits ahead of the previously qualified WSP Core revision.

Observed changed areas include:

- mining pool;
- miner;
- operations/release tooling;
- treasury/release checks;
- explorer/site/integration documentation and tests.

No changed file was observed in the Core wallet/transaction/consensus source areas on which the existing WSP implementation relies.

### Interpretation

This is a favorable compatibility signal, not a qualification result.

A rerun is still required because:

- build artifacts may differ;
- RPC behavior can be affected indirectly;
- dependency or packaging changes may alter integration;
- absence of a changed file is not proof of behavioral equivalence.

## Compatibility matrix

| Area | Existing evidence | Current status | Phase-1 action |
| --- | --- | --- | --- |
| secp256k1 / Schnorr primitives | Existing WSP uses coincurve/libsecp256k1 and native BIP-340/341-compatible signing paths | No relevant Core file delta observed | Re-run crypto/PSBT vectors |
| BIP-352 derivation | BIP-352 v1.1.1; official vectors and differential oracle | Existing implementation baseline available | Re-run full vector + differential gate |
| P2TR output/signing | Existing WSP supports native P2TR key-path signing | No relevant Core file delta observed | Re-run Core decode/finalize/broadcast integration |
| PSBT | Existing WSP uses PSBTv2 internally and exports compatible Core handoff | Current Core integration unqualified | Re-run PSBT handoff suite |
| Scanner chain source | Validating local WAM node, coherent height/hash pinning | Current head not yet rebound | Re-run two-node scanner E2E |
| Reorg handling | Existing 1/12/100/300 block tests | Logic already present | Re-run mandatory depths |
| Recovery | Authenticated recovery + full rescan evidence exists | Current head not yet rebound | Re-run recovery suite |
| RPC trust boundary | Local validating-node model | No production remote-node claim | Verify RPC methods/limits unchanged |
| Network namespace | `wamrtsp` regtest-only | Mainnet/testnet unresolved | Maintain unresolved status |
| External review | Pending | Pending | Do not label production conformant |

## Qualification gate

Phase 1 passes only when evidence is recorded against the current pinned Core revision.

At minimum:

1. build or obtain the exact current-Core test daemon;
2. record its digest;
3. run WSP contract tests;
4. run unit/adversarial/integration/recovery suites;
5. run mandatory two-node E2E and reorg depths;
6. run BIP-352 vectors and differential gate;
7. run protocol-sensitive fuzz targets if relevant implementation code changes;
8. produce a qualification report binding source revision, daemon digest, command results and report hashes.

Until then, status remains:

`CURRENT CORE REQUALIFICATION PENDING`
