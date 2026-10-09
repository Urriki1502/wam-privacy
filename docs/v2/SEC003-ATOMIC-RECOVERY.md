# SEC-003 cross-module atomic recovery contract

Status: conservative actual A/B research composition implemented; tests pending exact-HEAD CI. Distributed atomicity, production integration and full SEC-003 acceptance remain BLOCKED.

## Scope and source inspection

Research base V2 freeze: 5af86cfd5be27a3275079cbccde2abd2366ebb2b.
V1 freeze: 95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127.
No frozen files, Core, consensus or main changes. No network, wallet or funds.

Inspected frozen v2/policy.py and v2/bridge.py. PolicyAuthority.authorize mutates used, consent_used and clock highwater before returning ALLOW_POLICY_ONLY. LocalV1SignerBridge.sign then calls SignerGate.sign; policy consumption can therefore precede signer failure. Restoring an older independently valid policy snapshot must never compensate such a failure.

A proposed interface from agent A: DurablePolicy(db_path, grant_key, consent_verify_key) with operations that load and commit latest state in SQLite BEGIN IMMEDIATE, synchronous FULL. export_checkpoint() gives generation and snapshot; validate_checkpoint rejects anything except current trusted state. A checkpoint witness must be outside the attacker rollback domain. Rolling back the entire trusted database remains outside this guarantee.

B proposed interface from agent B: PersistentSignerGate(provider, journal_path, policy=None).sign(request, approval). A committed RESERVED precedes provider invocation; COMPLETE includes the durable result. Pending/uncertain outcome permanently blocks repeat signing. Identical completed binding returns cached result; changed request/approval/policy binding rejects. B has no public transaction reservation/receipt interface yet.

Pinned concrete dependencies: A 4f2a81acb66bfe35ae2ea0ec878e21f608f76130; B 059658db638229abac23f077e9318466bf501a63. The research coordinator composes these actual adapters without editing their files. CI overlays only their isolated research directories after verifying source pins.

## Threat model and trust boundary

An attacker can supply/replay old authenticated snapshots, trigger process death at any boundary, race request IDs, replace one participant's state with another epoch and swap request/result receipts. Trusted code controls request binding, monotonic witness, clock and consent issuer. Receipts must be authenticated and loaded from durable participant stores; arbitrary input strings to the pure checker do not establish this trust.

Atomic commitment across independent SQLite stores and an external signer is unavailable from current interfaces. Safety takes priority over retry liveness: unknown provider outcome consumes authority and remains blocked. Exactly-once external signing cannot be inferred from a local transaction log.

## Required intent and ordering

Before any side effect persist a unique transaction_id, canonical request binding, policy witness and PREPARED intent to a trusted durable coordinator. The canonical binding must cover network/account, canonical V1 request ID and transaction digest, complete approval and policy, V2 capability and consent nonce where applicable. Hash algorithms/serialization and receipts require joint A/B agreement before implementation.

Required forward-only sequence:

1. PREPARED intent committed before policy consumption.
2. POLICY_SPENT receipt committed only after A confirms durable grant/consent consumption.
3. SIGNER_RESERVED receipt committed before the signer provider can act.
4. COMPLETE committed only with B's authenticated durable result receipt.

A crash between participant commit and coordinator phase update must reconcile authenticated participant receipts. Missing, stale, unauthenticated or conflicting evidence blocks. Never infer that a provider did not act from missing COMPLETE. Reservation deletion or journal rollback blocks. A later policy generation can contain legitimate concurrent operations; generation alone cannot prove that this transaction's capability/consent is consumed. Integration requires a transaction-bound spent receipt, not only a highwater integer.

## Restart decision table

| Durable coordinator phase | Trusted policy spent | Signer receipt | Decision |
| --- | --- | --- | --- |
| PREPARED | no/yes | absent | New trusted authorization required; never restore consumed grant |
| POLICY_SPENT | yes | absent | New trusted authorization required; never refund authority |
| POLICY_SPENT | no | any | Block inconsistent/rolled back participant |
| SIGNER_RESERVED/COMPLETE | yes | absent | Block disappeared reservation/result |
| any | any | RESERVED/unknown | Block permanently; no provider retry |
| SIGNER_RESERVED/COMPLETE | yes | COMPLETE with matching request/result | Return durable cached result only |
| PREPARED/POLICY_SPENT | yes | COMPLETE | Block impossible early completion |
| any | any | stale policy generation or binding mismatch | Block |

REAUTHORIZE is an instruction for future trusted UI provisioning, not permission to automatically retry. RETURN_DURABLE_RESULT describes returning an already recorded result and never invokes the provider.

## Executable evidence scope

v2/sec003_research/contract.py is a pure conservative decision checker, not a coordinator and not a signer. test_contract.py serializes/reloads model intents at each cut and checks uncertain outcomes, missing reservations, policy rollback, swapped receipts, impossible phases and forward-only ordering. It does not implement authenticated receipts, fsync durability, process concurrency, A/B calls or provider side effects. A successful contract test run is CONTRACT TEST PASS only. Actual composition evidence is separately scoped below.

## Integration acceptance gates

Before changing status from BLOCKED:

- Agree A/B on canonical binding and transaction-bound durable receipt schemas.
- Add shared trusted transaction coordinator or authenticated durable participant reconciliation protocol. A/B independently committing SQLite records alone cannot provide atomicity.
- Implement real-process fault injection before/after each commit and before/after provider call, including kill and reopen from disk.
- Verify stale authenticated snapshots, whole policy-store replacement against independent witness, torn/absent journal, mismatched epochs, consent replay and revocation persistence.
- Race identical and different requests across threads/processes; provider counter must show at most one call per binding.
- Verify completion-before-response crash returns same cached result without provider reentry; uncertain outcome never retries, even after trusted restart.
- Execute integration against research A/B commits pinned by SHA and preserve original frozen V1/V2 regression evidence.
- Verify exact PR head checkout, test output, logs and artifact manifest at the same SHA. Report inherited freeze-policy CI failures without relaxing frozen rules.

CORE-003 remains production blocked pending maintainer approval. Independent security review and trusted UI integration remain external acceptance gates.


## Conservative concrete composition

coordinator.py implements DurableResearchBridge(authority, gate, path, account_scope, provision=False), requiring the actual pinned A/B types and research provider. It copies and validates the capability mapping before binding or callbacks, requires an immutable single-use SIGN grant, and binds exact request, approval, capability, account, signer identity, policy and capabilities.

The durable coordinator commits PREPARED before A authorization, records POLICY_SPENT only after A consumption is confirmed by exact immutable grant fields plus used tombstone, and commits SIGNING before invoking B. SIGNING is a conservative may-have-started phase; it is NOT a claim that B RESERVED already exists. COMPLETE is committed only after matching B's trusted durable COMPLETE receipt. An interrupted non-COMPLETE coordinator record remains permanently blocked, including a crash after B completed but before C recorded completion. This deliberately sacrifices recovery liveness.

Completed result delivery returns the durable cache after checking exact C binding, A consumed grant fields, minimum generation, current revocation/expiry/clock highwater and B binding/digest/envelope. Missing or mixed receipts block. B schema reading is private research coupling, pinned to the exact B SHA above. This is not a production adapter interface.

Revocation is ordered at A.authorize. A later concurrent revoke cannot recall a provider operation already authorized/in flight; this PR has no distributed revocation fence. Cached result delivery after observed revocation or expiry is denied.

All three stores and keys remain trusted, outside the rollback attacker domain. Independently rolling back A is detected against a surviving C receipt in the tested case; jointly rolling back all stores is NOT detected. SQLite FULL commits protect the tested process-restart boundaries under filesystem durability assumptions, not arbitrary hardware power loss or malicious storage.

test_composition.py uses actual A/B adapters, fixture provider and process death at PREPARED, A commit before receipt, POLICY_SPENT, SIGNING, provider call, B completion and C completion. It also tests multi-process provider at-most-once, restart cache, changed approval, expired/revoked cache delivery, missing B receipt, independently rolled back A state, missing coordinator, caller-mapping mutation and unrelated generation lacking consumption. No public network/node or real funds are used.

The CI manifest distinguishes conservative research composition tests from distributed ACID and production readiness. A passing targeted run establishes these tests at the recorded C/A/B SHAs only; full SEC-003 exit gates and independent review above remain open.

## SEC-003 integration refresh (SEC-001 / SEC-002 passed heads)

The CI checkout pins now use the verified current research heads SEC-001 `4f2a81acb66bfe35ae2ea0ec878e21f608f76130` and SEC-002 `059658db638229abac23f077e9318466bf501a63`, not older intermediate commits. SEC-002 introduced explicit trusted journal first-install `provision=True`; the isolated composition fixture now provisions the B store only on first install. No V1 or V2 freeze/runtime changes are included.

Coordinator bootstrap hardening follows the same fail-closed rule as SEC-002: ordinary opens require an existing SQLite file (`mode=rw`); only trusted first-install code may set `provision=True`, which rejects an existing coordinator file. A missing coordinator, missing B journal or changed local schema cannot silently restore signing authority. New tests cover deleted coordinator journal, prohibited reprovisioning and missing B journal. This addresses **implicit file recreation**, not malicious replacement, replay of all independently trusted stores, disk power-loss durability or distributed transaction atomicity. Full production qualification remains BLOCKED.

Only a same-HEAD GitHub Actions success with its pinned A/B SHA evidence can establish these new integration tests as passing. Earlier SEC-003 successes used older adapter heads and do not qualify this refresh.
