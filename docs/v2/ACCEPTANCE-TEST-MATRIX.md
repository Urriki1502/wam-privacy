# WAM Privacy V2 — Adversarial Acceptance Matrix

**Status:** test specification; not test results. A checked checkbox here requires a linked CI run and a deterministic fixture.
**Rule:** V1 release and V2 evaluation statuses must be tracked separately.

| ID | Abuse case / invariant | Expected result | Evidence to collect |
| --- | --- | --- | --- |
| CAP-001 | Unknown action/version/role | DENY, fixed error | parser negative vectors |
| CAP-002 | Scanner requests SIGN | DENY | key-compartment fixture |
| CAP-003 | Auditor requests spend authority | DENY | role isolation fixture |
| CAP-004 | Viewer requests full account export without scope | DENY | scope fuzz/property test |
| CAP-005 | Replay/duplicate grant used after completion | DENY | restart/replay regression |
| CAP-006 | Expired grant or clock regression | DENY | deterministic clock test |
| CAP-007 | Grant from testnet used on regtest | DENY | cross-network vector |
| CAP-008 | Grant from account A used for B | DENY | cross-account vector |
| CAP-009 | Untrusted remote claim of local privilege | DENY | malformed provenance fixture |
| CAP-010 | Revoked grant after process restart | DENY | persistence/revocation test |
| FLOW-001 | SCAN output includes spend secret | DENY/no secret in output | API/serialization assertion |
| FLOW-002 | Signed transaction path takes scanner approval as authorization | DENY | real PSBT signing-policy test |
| FLOW-003 | Audit event contains memo, seed or recipient list | REDACT | log inspection fixture |
| FLOW-004 | Disclosure request includes unauthorized note/value | DENY | projection property tests |
| FLOW-005 | Disclosure schema change strips scope or purpose | DENY | version migration tests |
| FLOW-006 | Disclosure is mistaken for a spend permission | DENY | capability non-escalation test |
| FLOW-007 | Reorg changes recognized note set | deterministic rollback/replay | 300-block reorg test |
| FLOW-008 | Wallet restart with same canonical history | equivalent recognized state | recovery differential test |
| NET-001 | Required private route fails | explicit failure, no clearnet fallback | synthetic transport failure |
| NET-002 | Same provider serves multiple public roles | reject or warn per explicit policy | endpoint correlation fixture |
| NET-003 | Broadcast service requests seed/view credentials | DENY | role-boundary fixture |
| NET-004 | Metadata observer sees IP + request timestamps | acknowledge remaining leakage, no anonymity claim | measurement methodology |
| CORE-001 | Capability layer changes proof balance | impossible by architecture; test equality to V1 verifier | regression bridge |
| CORE-002 | Capability layer attempts duplicate nullifier | Core rejects as before | regression bridge |
| CORE-003 | Capability layer accepts forged next_anchor | never trust caller; unresolved production integration gate | Core integration adversarial test |
| PERF-001 | Huge scope list or nested policy | bounded parse/memory/time | resource budget |
| PERF-002 | Large wallet/history export | bounded batch/size limits | benchmark |
| COMPAT-001 | New V2 behavior changes WAM Core consensus | prohibit pending explicit maintainer approval | source-drift check |
| COMPAT-002 | New cryptographic key derivation without review | prohibit pending independent review | version/interface gate |

## Test harness constraints

Use isolated/mock RPC and local regtest only, synthetic identities and keys, and never public pools or unapproved third-party endpoints. Keep the WAM Core source version pinned. All test evidence must identify exact git commit, dependency locks, policy schema version, test environment and runner limits.

## Release sequence

**V2-design:** architecture, threat model and compatibility matrix (this document).

**V2-policy-prototype:** after V1 logical freeze, implement a standalone application-layer authorization engine on a distinct V2 versioned branch, without modifying the V1 commit, live Core consensus or cryptographic circuits.

**V2-wallet-integration:** use existing validated signer/wallet policy interfaces with strict capability boundaries, then test in isolated regtest.

**V2-optional-privacy-transports/disclosure:** implementation requires independent threat/metadata analysis and explicit maintainer-alignment gate where architectural scope crosses wallet-only boundaries.

**V2-review:** code audit, adverse-case closure, measurable metadata/privacy limits and independent maintainer decisions before production claims.

## Quality measurement

Report: exact tests executed and failed, feature-surface coverage, number of confirmed unresolved P0/P1 findings, fuzz duration/corpus, cross-version compatibility, privacy leakage remaining for each observer, memory/time ceilings, independent-review confidence. Never replace these with an unsupported numeric "security %" assessment.
