# V2-02 — Wallet-local selective disclosure, research qualification

## Scope

Extends V2-01 capability authorization without modifying WAM Core, V1 Rust,
V1 crypto, consensus or wallet key formats. Works on local synthetic fixtures;
no live RPC, signer, relay or on-chain attestation.

## Security behavior

- User selects only a bounded, canonical tuple of supported fields:
  txid, amount_atoms, block_height. No memo/seed/account-history export.
- A separate UI-controlled SelectionIssuer MACs the exact requested fields,
  policy request, unique V2-01 consent nonce and expiration.
- The local DisclosureService checks field MAC and locally validated wallet
  record scope before consuming V2-01's single-use consent.
- Export contains only selected fields plus minimal purpose/resource/network
  context. Receipt, account scope, capability IDs, internal audit/session info
  and private wallet metadata are never exported.
- Decision events are fixed redacted codes; no txid, account, seed, recipient,
  memo, IP, amount, session or request payload in event fields.
- Max 3 disclosed fields, max 1024 locally indexed records and max 2048 bytes
  per disclosed object; duplicate record keys and malformed numeric fields
  fail closed.
- V2-01 consent replay and revocation survive signed restart snapshots. New
  selection approvals are cryptographically bound to a *specific* consent
  nonce and cannot be carried over to the next UI approval.
- This is a local projection of wallet data, NOT a cryptographic ownership
  proof, ZK selective proof, digital audit attestation, or permission to sign.

## Essential integration caveats

- Trusted UI MUST independently display and confirm exact fields, purpose,
  scope and recipient before calling both issuers. These HMAC receipts are
  only authentication between trusted local components, not proof of human
  presence. Untrusted RPC callers must not hold issuer keys or objects.
- Wallet records must come from authenticated local wallet state, not remotely
  provided data. Current fixtures do not prove WAM ownership of records.
- State snapshot authenticity does not prevent replay of an older valid
  snapshot. Production-quality persistence requires an atomic trusted,
  rollback-resistant store and crash-safe consumption before external release.
- V2-02 does not implement revoke-after-disclosure, stop recipient retaining
  disclosed facts, hide public chain metadata, or control downstream data use.
- PERF-001 nested/large arbitrary policies remains a V2-01/parser or later
  integration task, not falsely claimed here. PERF-002 local count/output
  ceilings are deterministic policy bounds; full wallet throughput benchmarks
  remain pending.
- FLOW-003/004/005/006 are covered at the local projection/receipt layer,
  not a production wallet/RPC/export implementation.

## Follow-on

V2-03 is route policy simulator and observer fixtures. V2-04 integrates with
real WAM wallet interfaces, reorg/restart, signer boundaries and information
flow acceptance tests. No automatic merge into main or V1 release.
