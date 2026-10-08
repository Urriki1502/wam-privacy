# WAM Privacy V2 — Information-Flow and Capability Architecture

**Status:** DESIGN ONLY — no V2 runtime implementation, consensus changes, public release, or activation.
**Source baseline:** V1 security remediation merged at `15fafa199871f7a1688b1beda5e27005ae473d27`; post-merge qualification merged as `d3d6fb4ae877de02b2b99749c673a698dbf98b19`.
**V1 relationship:** preserve V1 immutable source semantics. V2 code begins only after an independently recorded internal logical freeze, and only on a separate versioned branch. The public V1 release still depends on external review/testnet evidence.

## Product goal and differentiator

Make WAM wallet privacy **measurable and least-privileged** rather than inventing a new blockchain or replacing WAM Core. A scanner, viewer, signer, broadcaster, disclosure service and auditor should receive only the data and authority needed for a specific task. Separation should survive malicious provider responses, key theft limited to one compartment, wallet restart and chain reorganization.

This design draws on information-flow control ideas (including the principle of selective views of data) without copying a particular platform's implementation or claiming compatibility with Canton or any privacy protocol.

## Hard constraints

1. Supply cap remains 22,000,000 WAM (100,000,000 atomic units/WAM). Never weaken conservation, nullifier uniqueness or shielded-pool solvency.
2. Do not change WAM Core consensus, network activation, serialization, proof circuit or viewing/spending key formats under this V2 design.
3. Preserve V1 proof and VK identity when evaluating new wallet-side features. Cryptographic changes require a separate version, full qualification and independent review.
4. Use established primitives; do not invent new encryption or zero-knowledge constructions.
5. Require caller, scope, purpose, expiry/session, network and provenance checks at each trust boundary, with default-deny behavior.
6. Treat all provider metadata and wallet history as untrusted until validated; no "scanner says spendable" authority.
7. Distinguish *data visibility* from *ability to spend*. Network transport encryption does not equal transaction-origin anonymity.
8. All externally publishable privacy claims require a named observer model, leakage analysis, repeatable tests and limitations.

## Threat model and observers

| Observer | Can observe/control | Target property | Remaining limitation |
| --- | --- | --- | --- |
| Curious RPC provider | request timing, addresses, scanning queries | local-first scans; minimize wallet identifiers and cross-request linkage | provider still sees its own traffic |
| Compromised scanner | scan credentials, recognized notes | cannot obtain spend authority or submit approved signatures | can expose notes visible to the scanner |
| Compromised viewer | decrypted note plaintext and history | cannot sign or create audit grants | viewed metadata may still be copied |
| Malicious coordinator | transaction proposals, peer timing, fee changes | signer independently verifies canonical transaction and explicit approval | signed transaction and broadcast metadata remain observable |
| Compromised broadcaster | pending tx, route endpoints | receives no spend seeds or scanner database | can link transactions that pass through it |
| Curious/disloyal auditor | permitted disclosure materials | sees only explicitly authorized fields; cannot spend | disclosed facts may be retained forever |
| Passive network observer | subset of network flows, clocks, addresses | distinguish sender metadata in measurement | global observers and timing attacks remain out of scope without evidence |
| Chain observer | public inputs, nullifiers, commitments, fees | preserve existing V1 cryptographic privacy and invariants | public transaction timing/shape is still visible |

## Capability boundaries

A "capability" is a locally enforceable authorization to *perform one action*, not an authority inferred from possession of a generic wallet object.

| Action | Required permission | Minimum input | Secrets forbidden |
| --- | --- | --- | --- |
| SCAN | chain-scan | canonical chain history + incoming viewing authority | spend seed/key |
| VIEW | note-view | explicit account/note scope | spend key |
| SIGN | spend-authorize | canonical transaction, spend intent, network, policy, user approval | auditor credential; scanner-only approval |
| BROADCAST | tx-broadcast | finalized transaction bytes, validated route policy | seed/viewing key |
| DISCLOSE | selective-disclose | user-authorized field list and purpose, bounded lifetime | spend authority; unrelated account history |
| AUDIT | disclosure-audit | redacted decision events or narrowly scoped disclosures | payment keys, whole note store by default |

Never let one permission implicitly grant another. Do not encode privileges as a bitmask that grants transitive authority. Capability grants are immutable, scoped, validated per use, revocable where meaningful, and excluded from user-facing logs.

## Proposed information-flow labels (wallet/local policy only)

- `PUBLIC`: protocol params and externally published material;
- `CHAIN_METADATA`: observed block/transaction data, no wallet identity;
- `ACCOUNT_METADATA`: account/note ownership and spend history;
- `NOTE_PLAINTEXT`: decrypted values/memo/recipient relationships;
- `SPEND_SECRET`: seed and spend-signing authority;
- `AUTHORIZED_DISCLOSURE`: explicit user-approved projection from more sensitive data, not an unrestricted declassification.

**Allowed directions:** scanner may receive CHAIN_METADATA and account-specific incoming viewing access; viewer receives an explicit NOTE_PLAINTEXT projection; signer receives canonical transaction intent and isolated spend authority; broadcaster receives finalized bytes only; disclosure issuer receives only a user-approved projection; auditor receives only that projection and redacted decision provenance.

**Forbidden flows:** SCAN→SIGN authorization; VIEW→SIGN authorization; AUDIT→SIGN; BROADCAST→SCAN database; default NOTE_PLAINTEXT→network logs; unrestricted DISCLOSE→full wallet export.

## Deterministic policy evaluation

Proposed request fields: `actor_role`, `capability_id`, `action`, `account_scope`, `resource_scope`, `network_id`, `purpose`, `expires_at`, `session_id`, `policy_version`. Evaluate in this order:

1. Parse and bound all fields (reject malformed or unknown version).
2. Verify grant provenance and context binding; never trust unverified remote "capability" claims.
3. Enforce network, account/resource scope, exact action and expiry.
4. Apply information-flow labels and explicit user consent for any declassification.
5. For SIGN, separately validate canonical transaction/PSBT, fee/value policy, replay and user-approved intent using existing signer boundary.
6. Emit a redacted decision code (no raw keys, memo, full wallet IDs, transaction bytes or recipient graphs).

A capability decision does not replace cryptographic signature, ZK proof verification or Core consensus validation.

## Selective disclosure — proposed V2 application profile

Start with an explicit **wallet-local export of narrowly selected facts**: named set of recognized notes, bounded amount/time projection if user approves, context and purpose, disclosure schema/version, and unambiguous non-claims. Keep disclosed data separate from authority and spending keys.

Do not claim cryptographic zero-knowledge selective disclosure until an actual independently reviewed proof construction is specified and tested. Consider proof-backed attestations only as a later extension needing maintainer alignment and protocol-versioning decisions.

## Metadata-aware broadcast — proposed V2 opt-in

Keep scanning local by default, choose broadcast routes with separate endpoint/credential isolation, do not silently fall back to clearnet when a user explicitly requires a private route, avoid logging network identifiers, and support deterministic simulated route-failure tests. No automatic global anonymity claim.

## State and recovery

Persist versioned capability policy configuration, not raw grants or spend secrets by default. Re-scan/reorg must reconstruct ownership consistently independent of disclosure audit records. Every revoked/expired grant must remain rejected after process restart. Time-sensitive decisions require a trustworthy local clock abstraction for tests; clock rollback must fail closed where expiry is security-critical.

## Open integration questions (not implementation authorization)

- Whether relay policy should be wallet-only or require upstream WAM network changes: **NEEDS_MAINTAINER_CONFIRMATION**.
- Whether disclosure attestations should ever be on-chain or proof-backed: **NEEDS_MAINTAINER_CONFIRMATION**.
- Whether V2 may extend versioned key derivation/profile identifiers: **NEEDS_MAINTAINER_CONFIRMATION**.
- WAM Core canonical commitment tree and next-anchor derivation: existing V1 regtest trust boundary; **not silently solved by V2 capability design**.

## Evidence required before V2 security claims

Each property requires positive and negative vectors, untrusted-provider tests, key-compartment compromise tests, replay/expiry/revocation tests, restart/reorg tests, redacted-event assertions, performance limits and independent review when crypto or protocol semantics are touched. See `docs/v2/ACCEPTANCE-TEST-MATRIX.md`.
