# V2-04 — Frozen V1 signer bridge, Rust regression and compatibility gates

**Status:** research-only, draft/stacked integration evidence; never a production-ready
release or Core activation. Source base: V2-03 head
`403fb4889c97a680f3deabdb2a1c0db3fb6c65fd`. V1 logical source pin:
`95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127`.
Qualified WSP adapter dependency:
`Urriki1502/wam-silent-payments@dcf1aecc00a64bfad3151fa202c3e07d47d83e69`.
Historically pinned Core reference:
`wamcoin-core-dev/wam-coin@260bc468e5adffea7ce68d8f97fac3e27e4c50b2`.
These pins are NOT evidence of a current upstream Core integration.

## Actual code introduced (V2-only)

- `v2/bridge.py`: a narrowly scoped, **local regtest/testnet-only**
  `LocalV1SignerBridge` combines a V2 SIGN grant bound to an already
  canonical V1 `SignRequest.request_id`, local account and network with
  **independent** frozen V1 `SignerGate` plus V1 `Approval`. It does not
  parse PSBT itself, issue grants, capture real UI consent, hold keys,
  derive cryptography, send RPC or broadcast transactions.
- `v2/test_bridge.py`: positive/negative role, capability, resource, account,
  network, expiry, revocation, restart/replay, fee, recipient and V1
  provider boundary cases. FixtureSigner is NON-cryptographic.
- `v2/test_wsp_bridge.py`: actual canonical pinned WSP PSBT parsing and
  cryptographic signing through the unmodified frozen V1 WAM adapter,
  Phase 3 signer gate and V2 capability boundary; only synthetic keys,
  regtest, no sockets, no actual node transaction submission.
- Dedicated `.github/workflows/v2-04-v1-bridge.yml` has four jobs:
  (1) standalone V2+V1 signer boundary tests,
  (2) WSP pinned real PSBT/Schnorr tests,
  (3) existing Rust V1 shielded scanner/reorg/proof/state regression,
  (4) V1 source drift and Core-compatibility guard.

## Acceptance evidence / precise limitations

| ID | Work | Qualification |
| --- | --- | --- |
| CAP-005, CAP-010 | Signed local grant single-use and revocation survive process-state snapshot restoration | Local V2 replay/revocation fixture, **not durable secure storage** |
| FLOW-002 | V2 policy-only SIGN cannot bypass independent V1 Approval or signer validation | V2-04 Python fixture + WSP real signer, no human UI integration |
| FLOW-007 | Known wallet notes roll back on reorg; V1 Core state handles 300-block rollback/replay | Existing frozen Rust V1 `wallet_state` and `core_state::tests` re-executed, **not one shared production wallet/Core instance** |
| FLOW-008 | Canonical history reconstructed by V1 wallet full rescan; policy grant single-use/revoke state survives local snapshot restart | V1 scanner deterministic rescan + V2 local snapshot, **not atomic crash-safe joint wallet/ledger persistence** |
| CORE-001 | V2 changes cannot modify V1 balance/proof inputs; real proof-verified V1 state still balances under existing tests | Frozen-source check + `core_state_proof` + `security_domain_binding`; **not live Core consensus proof integration** |
| CORE-002 | V1 atomic state rejects duplicate nullifiers | Existing frozen Rust core-state negative unit test, no V2 permission to override |
| CORE-003 | Production Core must independently derive canonical commitment-tree next_anchor and reject forged caller root | **BLOCKED/UNRESOLVED**: current V1 `StateBlock.next_anchor` is caller-supplied and canonical *encoding* is checked, not *root derivation*. Do NOT label PASS |
| COMPAT-001 | No changes to V1 crypto, Rust Core adapter, consensus or source identity in V2-04 | Git source-drift checks from V1 freeze and V2-03 base. Not a WAM Core runtime integration |
| COMPAT-002 | No new derivation or key format, fixed WSP dependency | Diff path restriction + source pin only. Independent crypto/key audit not performed |

## Boundaries / remaining release blockers

1. `Bridge.sign` MUST be called by trusted wallet-local code; its issuer key
   and `PolicyAuthority` instance must never be remote-accessible. `Approval`
   must come from an independent trusted UX/session authorization flow;
   V2-04 does **not** implement actual hardware-backed user presence.
2. Research-only bridge rejects mainnet. A V2 ALLOW cannot replace V1
   signer policy, PSBT-derived ID, ownership classification or approvals.
   SignerGate is intentionally V1, not reimplemented in V2.
3. A one-shot grant is marked used when the V2 authorization succeeds;
   subsequent V1 signing rejection does not restore the grant. This prevents
   automatic replay, but user recovery requires trusted re-issuance.
4. V2 snapshot MAC is not proof of *anti-rollback*: malicious restoration of
   an older valid snapshot remains open until a wallet-controlled monotonic
   secure checkpoint is implemented.
5. The Rust scanner and Core state run existing independent fixtures.
   There is no process-atomic bridge from Rust V1 state to this Python V2
   signer adapter, no real Core node and no validated persistent wallet DB.
6. Production shielded validity remains **blocked** on canonical
   `next_anchor` computation, long-lived tree state, depth and Core review.
   External Phase15C/D audits and maintainer decisions remain pending.
7. This phase makes **no claim** of privacy anonymity, live relay delivery,
   production durability, consensus compatibility verification on a live
   node, or permission to spend real WAM.

## Evidence protocol

The authoritative test results are the exact PR head's GitHub Actions run
conclusions, **not** this design/qualification document. Green tests
demonstrate only the cases above. After CI finishes, V2-05 should record
the immutable head SHA, run links, Python/Rust versions, full 29-case matrix,
known failures/blocked gates, independent review requests and clean-clone
reproduction commands. Never automatically merge V2 branches to `main`.
