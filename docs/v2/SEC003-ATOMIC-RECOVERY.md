# SEC-003 cross-module atomic recovery contract

Status: design and contract tests only. A/B integration BLOCKED; no production, atomicity, cryptographic review or security PASS claim.

## Scope and source inspection

Research base V2 freeze: 5af86cfd5be27a3275079cbccde2abd2366ebb2b.
V1 freeze: 95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127.
No frozen files, Core, consensus or main changes. No network, wallet or funds.

Inspected frozen v2/policy.py and v2/bridge.py. PolicyAuthority.authorize mutates used, consent_used and clock highwater before returning ALLOW_POLICY_ONLY. LocalV1SignerBridge.sign then calls SignerGate.sign; policy consumption can therefore precede signer failure. Restoring an older independently valid policy snapshot must never compensate such a failure.

A proposed interface from agent A: DurablePolicy(db_path, grant_key, consent_verify_key) with operations that load and commit latest state in SQLite BEGIN IMMEDIATE, synchronous FULL. export_checkpoint() gives generation and snapshot; validate_checkpoint rejects anything except current trusted state. A checkpoint witness must be outside the attacker rollback domain. Rolling back the entire trusted database remains outside this guarantee.

B proposed interface from agent B: PersistentSignerGate(provider, journal_path, policy=None).sign(request, approval). A committed RESERVED precedes provider invocation; COMPLETE includes the durable result. Pending/uncertain outcome permanently blocks repeat signing. Identical completed binding returns cached result; changed request/approval/policy binding rejects. B has no public transaction reservation/receipt interface yet.

These proposals are dependencies, not APIs assumed integrated by this PR.

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

v2/sec003_research/contract.py is a pure conservative decision checker, not a coordinator and not a signer. test_contract.py serializes/reloads model intents at each cut and checks uncertain outcomes, missing reservations, policy rollback, swapped receipts, impossible phases and forward-only ordering. It does not implement authenticated receipts, fsync durability, process concurrency, A/B calls or provider side effects. A successful contract test run is CONTRACT TEST PASS only.

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
