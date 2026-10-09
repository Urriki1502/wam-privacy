# SEC-001 durable policy research

Scope: defensive local synthetic tests over immutable V2 policy.py at 5af86cfd5be27a3275079cbccde2abd2366ebb2b. No Core, consensus, wallet, funds, or public node.

Threat model: attacker can replace exported authenticated wallet snapshots, but cannot modify, roll back, or delete the separately protected trusted checkpoint database or keys. Storage corruption and missing store fail closed; startup never provisions by default. The explicit provision=True flag is trusted first-install administration only and must not be exposed to recovery or RPC.

SQLite is a durable reference backend, **not a hardware monotonic counter**. Whole-database or whole-disk rollback, malicious provision/reset, filesystem durability lies, device loss, and trusted-key compromise are outside the tested protection. Production remains blocked until a separately reviewed OS/hardware or remote trusted checkpoint backend enforces this boundary. A same-disk freely rollbackable database does not satisfy it.

Invariant: all mutations, grant/revocation, clock highwater, single-use consumption and consent nonce consumption commit with generation inside BEGIN IMMEDIATE / synchronous FULL before ALLOW_POLICY_ONLY returns. Each operation authenticates and restores latest frozen PolicyAuthority state. A crash after commit but before delivery may burn authority; no automatic retry of external side effects. Failed operations roll back. Multiple connections serialize.

Exported checkpoints contain generation, frozen authenticated snapshot, and SHA256. Validation compares all fields exactly to authoritative current state; it never imports external data. Equal current checkpoint validation is idempotent. Older, future and same-generation fork checkpoints are rejected.

C contract: DurablePolicy(path,gkey,ckey,provision=False); issue_local_grant, revoke, authorize(request,now,consent), export_checkpoint, validate_checkpoint, close. C must not call provider/sign/disclosure before durable policy authorization. Shared atomic signer-policy storage is not implemented: SEC-003 integration remains pending. Direct frozen LocalV1SignerBridge expects PolicyAuthority isinstance and cannot use this wrapper without a separately reviewed research composition.

Tests: 12 SEC-001 tests plus original V2 policy/bridge/disclosure/routing tests in exact-head CI. Process exit tests uncommitted rollback; restart tests validate committed consume/revoke/consent. Power-loss fault injection, disk-full, cross-process contention and hardware checkpoint qualification remain outstanding. No test result is claimed before GitHub run verification.

## SEC-001 follow-up: separately trusted monotonic witness

The initial research wrapper cannot detect a **whole database rollback**: an
old HMAC-valid row with an old generation and grants is internally consistent.
The new optional `checkpoint_witness` protocol is an independent, atomic
compare-and-advance generation/digest witness. This adds a fail-closed
**research integration contract**: every read compares the authenticated
SQLite snapshot to independently witnessed generation/digest; on every
mutation the witness must durably advance before SQLite COMMIT; only after
SQLite COMMIT returns may `ALLOW_POLICY_ONLY` leave the adapter.

If the process fails after the trusted witness advanced but before SQLite
commit, the DB is intentionally stranded behind the witness. Recovery MUST
fail closed and escalate to a trusted recovery procedure; automatic reset,
resigning old state or rewinding the witness is forbidden. This prioritizes
safety over availability and **does not implement crash-recovery liveness**.

The test `MemoryWitnessForTests` is process-memory *only* and therefore
**not suitable for production** or a true restart after losing the witness.
Production requires an independently provisioned tamper/rollback-resistant
storage provider with atomic durable CAS, stable identity/key custody and
tested power-loss behavior. Passing tests with the memory fixture is not
proof of that provider.

Backwards compatibility: SEC-003 pinned to prior A research SHA still uses
the original `DurablePolicy(path,grant_key,consent_key)` call signature. That
mode is intentionally unprotected from whole-DB rollback and remains
production BLOCKED. The new keyword is opt-in to avoid breaking other
unmerged research; production callers must never silently treat an
unwitnessed instance as secure.

New adversarial tests include an old authenticated **whole-store rollback**,
unwitnessed replay negative evidence, absence/outage of witness, trusted
advance failure, crash after witness CAS before SQLite COMMIT, concurrent
connections sharing a trusted witness, and restart/revocation/consumption.
