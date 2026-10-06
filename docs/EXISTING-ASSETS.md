# Existing Assets

The privacy program starts with reusable work, not a blank repository.

## 1. WSP-1 qualification implementation

Repository:

`Urriki1502/wam-silent-payments`

Branch:

`feat/wsp1-v1.0`

Status:

`1.0.0.dev0` / external audit and production-network adoption pending.

### Existing capabilities

The repository already implements or documents:

- BIP-352 payment derivation;
- BIP-352 official vector coverage;
- scan/spend secret separation;
- durable scanner state;
- atomic per-block commits;
- deterministic rollback;
- restart and recovery behavior;
- deep reorg validation;
- wallet accounting;
- PSBTv2 construction and offline signing;
- WAM SDK integration;
- fail-closed unsupported-policy handling;
- deterministic qualification reporting.

### Existing verification evidence

Recorded qualification documentation reports:

- 150 unit/adversarial/integration/migration tests passing;
- all 28 BIP-352 vector groups passing;
- 10,000 independent differential cases with no mismatch;
- more than 1,000,000 coverage-guided fuzz executions across nine targets;
- two-node E2E validation;
- deep-reorg validation at 1, 12, 100 and 300 blocks;
- reproducible wheel build evidence.

These are **internal engineering results**, not an external cryptographic/security audit.

## 2. Previously qualified Core profile

The WSP repository records:

- WAM Core v0.1.11;
- commit `8a3f4fe4f1d804c378f795d4cc281ec5125f75f3`;
- regtest-only network qualification;
- regtest WSP namespace `wamrtsp`;
- production network namespace/profile adoption unresolved.

## 3. Current WAM Core target

Phase 0 observed current WAM Core head:

`260bc468e5adffea7ce68d8f97fac3e27e4c50b2`

It is 41 commits ahead of the WSP-qualified baseline.

The observed file delta is concentrated in pool, miner, operations, release/site and related tests. No changed file was observed in the Core wallet/transaction/consensus source areas used by WSP.

This reduces migration risk, but does not replace qualification.

## 4. Reuse policy

Do not copy large bodies of WSP code into `wam-privacy` by default.

Prefer:

1. pinning the existing implementation;
2. reviewing and requalifying it;
3. extracting stable specifications/interfaces here;
4. moving code only when ownership or long-term architecture clearly requires it.

This avoids two diverging Silent Payments implementations.
