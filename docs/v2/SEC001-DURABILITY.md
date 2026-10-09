# SEC-001 durable policy research

Scope: defensive local synthetic tests over immutable V2 policy.py at 5af86cfd5be27a3275079cbccde2abd2366ebb2b. No Core, consensus, wallet, funds, or public node.

Threat model: attacker can replace exported authenticated wallet snapshots, but cannot modify, roll back, or delete the separately protected trusted checkpoint database or keys. Storage corruption and missing store fail closed; startup never provisions by default. The explicit provision=True flag is trusted first-install administration only and must not be exposed to recovery or RPC.

SQLite is a durable reference backend, **not a hardware monotonic counter**. Whole-database or whole-disk rollback, malicious provision/reset, filesystem durability lies, device loss, and trusted-key compromise are outside the tested protection. Production remains blocked until a separately reviewed OS/hardware or remote trusted checkpoint backend enforces this boundary. A same-disk freely rollbackable database does not satisfy it.

Invariant: all mutations, grant/revocation, clock highwater, single-use consumption and consent nonce consumption commit with generation inside BEGIN IMMEDIATE / synchronous FULL before ALLOW_POLICY_ONLY returns. Each operation authenticates and restores latest frozen PolicyAuthority state. A crash after commit but before delivery may burn authority; no automatic retry of external side effects. Failed operations roll back. Multiple connections serialize.

Exported checkpoints contain generation, frozen authenticated snapshot, and SHA256. Validation compares all fields exactly to authoritative current state; it never imports external data. Equal current checkpoint validation is idempotent. Older, future and same-generation fork checkpoints are rejected.

C contract: DurablePolicy(path,gkey,ckey,provision=False); issue_local_grant, revoke, authorize(request,now,consent), export_checkpoint, validate_checkpoint, close. C must not call provider/sign/disclosure before durable policy authorization. Shared atomic signer-policy storage is not implemented: SEC-003 integration remains pending. Direct frozen LocalV1SignerBridge expects PolicyAuthority isinstance and cannot use this wrapper without a separately reviewed research composition.

Tests: 12 SEC-001 tests plus original V2 policy/bridge/disclosure/routing tests in exact-head CI. Process exit tests uncommitted rollback; restart tests validate committed consume/revoke/consent. Power-loss fault injection, disk-full, cross-process contention and hardware checkpoint qualification remain outstanding. No test result is claimed before GitHub run verification.
