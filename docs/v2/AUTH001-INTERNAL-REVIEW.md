# AUTH-001 internal boundary review and research contract

Review status: internal research assessment, 2026-10-09. No independent external Phase 15C/D audit or independently verified reviewer identity is claimed.

Reviewed V2 5af86cfd5be27a3275079cbccde2abd2366ebb2b and V1 95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127. Frozen sources and WAM Core/consensus remain unchanged.

## Findings / deployment blockers

AUTH-001 OPEN: v2/policy.py ConsentIssuer.issue_after_user_confirmation and v2/disclosure.py SelectionIssuer.issue_after_user_confirmation explicitly delegate user presence to trusted callers. Cryptographic receipts do not establish authentic UI origin. No actual wallet UI wiring was verified. The isolated LocalConsentBoundary adapter is a reference construction requiring a locally installed confirmer, clock, issuers and service; RPC must never construct it, inject callbacks, invoke issuers, or access keys. Real UI isolation and deployment acceptance remain OPEN.

DISC-001 OPEN acceptance: v2/disclosure.py DisclosureService.disclose always exports network_id, resource_scope and purpose, in addition to selected facts. These identifiers can correlate exports even when only txid is selected. Prompt explicitly lists mandatory metadata and the complete request scope. Product UI must display the actual values, recipient/destination and retention consequences, and obtain confirmation before release. AuditEvent contains fixed codes only. This review does not establish transport metadata privacy.

FFI-001 OPEN integration evidence: V1 prototypes/zk_balance_halo2/src/ffi.rs uses catch_unwind and early null/length/network/amount checks. Unsafe caller contracts still require live owned handles, valid buffers, and no free concurrent with verification; catch_unwind does not contain undefined behavior. C++ integration needs RAII ownership, serialized destruction, owned immutable buffers and trusted transaction context. Existing tests/ffi_bridge.rs covers malformed envelopes and context/proof rejection, not full C++ lifetime integration. No invalid-pointer experiments or new FFI runtime claim are made here.

SEC-001 dependency: PolicyAuthority.restore authenticates snapshots but its docstring explicitly requires external monotonic storage for rollback prevention. Latest-snapshot restart tests alone are insufficient for old-valid-snapshot rollback. SEC-003 must commit consent consumption before export; ambiguous crash after consumption returns no payload and requires fresh UI approval. Adapter lock serializes only calls through one adapter instance, not independent service instances/processes.

## Local authority contract

Trusted bootstrap exclusively owns grant provisioning, revoke, receipt issuers and clock. Untrusted RPC may submit bounded exact-schema request and sorted allowlisted fields only. Copy the request before display; display exact scope, purpose, session, network, expiration, selected facts and mandatory export metadata. A trusted confirmer must independently verify user intent; a client boolean is never authority. Deny cancellation, unavailable UI, invalid or expired clock, malformed fields, changed grant/revocation, missing consent or selection. Recheck policy at release.

The adapter mints short-lived receipts only after local confirmation, calls the actual frozen DisclosureService, and never returns receipts/keys to clients. It does not persist state or solve rollback; A/C interfaces must be integrated before production. No public node, real wallet or funds are used.

## Validation scope

Eight unittest cases exercise actual policy/disclosure APIs plus the adapter, including cancellation/truthy values, forbidden RPC confirmation, scope mutation, revocation during UI, malformed/expired input, UI failure and latest authenticated restart consent denial. Existing frozen policy/disclosure suites run as regression. CI checks out the exact PR HEAD and uploads SHA/test logs. Pending execution is not PASS. No independent crypto audit, C++ runtime audit or production UI acceptance is claimed.
