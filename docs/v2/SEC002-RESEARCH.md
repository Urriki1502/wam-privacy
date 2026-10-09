# SEC-002 research journal
Base V2: 5af86cfd5be27a3275079cbccde2abd2366ebb2b. Frozen V1 provider/model imported unchanged from prototypes/signer_abstraction; V1 freeze 95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127.

PersistentSignerGate(provider, journal_path, policy=None).sign(request, approval) implements durable RESERVED -> COMPLETE. RESERVED commits before invoking the frozen gate. An identical COMPLETE retry returns cached SignedResult, never invoking provider again. A conflicting request/approval/policy fails REQUEST_BINDING_MISMATCH. RESERVED retry fails REQUEST_PENDING. All uncertain failures retain reservation. This intentionally trades liveness for at-most-once provider invocation; there is no automatic retry/reconciliation.

SQLite FULL synchronous DELETE journal and BEGIN IMMEDIATE serialize reservations across processes. Hex identifiers canonicalize to prevent casing aliases. Frozen validation runs before accessing cached results. SQL failures propagate and no signing occurs before a confirmed reservation commit.

Threat boundary: journal file and containing directory must be pre-provisioned in trusted, private, nonrollback durable storage. SQLite is not a trusted monotonic checkpoint and does not detect authenticated whole-device rollback, malicious file replacement, lost directory durability, or deleted/recreated database. No production claim. Storage quota/cleanup/encryption, trusted signer reconciliation, consent authority and cross-module atomic integration remain blockers. Do not restore this journal from wallet snapshots or expire RESERVED entries. Use synthetic regtest fixtures only.

CI tests frozen provider/model blob identities, restart/idempotence, binding conflicts, concurrency, provider uncertainty and subprocess crash after provider invocation. Exact push SHA is printed and stored as artifact; CI outcome must be observed separately.

Signer binding includes caller-provisioned stable signer_identity and provider capabilities. Default identity is research-fixture for synthetic tests only. Integrators must provision identity from a trusted key/provider authority; labels supplied by untrusted callers are not authority. Schema initialization connection closes explicitly.
