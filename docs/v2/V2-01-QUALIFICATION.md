# V2-01 — Capability policy acceptance and trust boundary

Status: standalone wallet/application-layer research; no V1 modification, production permission or Core integration.

## Implemented in this phase

- Strict typed/size-bounded request with six independent roles and actions.
- Exact account, resource, session, purpose, network and expiration matching; no wildcard access.
- Local trusted grant issuance and authenticated grant/snapshot integrity using domain-separated HMAC-SHA256.
- A separate trusted UI consent issuer for DISCLOSE; consent receipt is bound to one exact request, expiry and single-use nonce.
- Replay prevention for single-use grants and all disclosure receipts; revocation and monotonic-clock witness survive signed snapshot/restore.
- Every authorized result is ALLOW_POLICY_ONLY, never a signature, disclosure operation or consensus authorization.
- Independent V1 source-drift and freeze gates run next to the isolated V2 tests.

## Trust limits, explicitly NOT solved

- Trusted wallet integration MUST own grant issuance, keys and the local clock. The untrusted request handler must not receive a PolicyAuthority or ConsentIssuer reference.
- The separate UI MUST authenticate real user approval BEFORE minting a receipt. Minting a receipt does not itself prove user presence.
- HMAC protects saved state against modification, not rollback to an older already-authenticated snapshot. Rollback-resistant trusted storage is required for high-assurance persistence.
- This prototype has no real PSBT signer enforcement, wallet persistence backend, receipt delivery, runtime relay, Core modification or public network operation.
- SCAN/VIEW/SIGN/BROADCAST/AUDIT are policy decisions only; subsequent runtime enforcement needs independent integration tests.

## Acceptance evidence

V2-01 CI tests positive and negative capability requests, field bounds, cross-account/network scopes, grant provenance, revoked/expired grants, replay after restart, monotonic clock rollback, consent forgery/replay/scope expiry and V1 source isolation.

The V2 design acceptance matrix in draft PR #50 remains broader than this module: FLOW-001/002/003/004/005/006 involving real wallet/PSBT/log/disclosure runtime, and independent audit are NOT claimed here.

Next work begins only when these gates pass on the final PR head. Remain Draft until V1 regression gates and mergeability are verified.
