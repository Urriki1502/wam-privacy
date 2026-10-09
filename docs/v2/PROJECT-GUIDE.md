# WAM Privacy — Project Guide

> **Research-only maintainer navigation.** A link to a passing CI run is evidence for that specific source and test scope, not integration authorization.

[Overview](../../README.md) · [Architecture](#system-dependencies) · [Branch topology](#branch-topology-and-review-links) · [Safety gates](#integration-and-acceptance-gates) · [Review checklist](#maintainer-review-sequence)

## System dependencies

The stack is intentionally split between **wallet-side behavior** and **potentially consensus-sensitive shielded state**.

~~~mermaid
flowchart TD
    CHAIN["WAM Core block history"] --> SCAN["WSP-1 scanning / recovery"]
    SCAN --> STATE["Wallet state / observations"]
    STATE --> P["V2 capability policy"]
    P --> UI["Trusted user approval"]
    UI --> SIGN["Signer journal / signer"]
    SIGN --> PSBT["PSBT / PayJoin transaction"]
    PSBT --> NET["Relay policy"]
    P --> C["SEC-003 consistency model"]
    SIGN --> C
    C -. "needs trusted stores + reconciliation" .-> STORE["Independent rollback-resistant authority"]
    STATE --> SHIELD["Shielded state research"]
    SHIELD --> VERIFIER["Halo2 verifier model"]
    VERIFIER -. "unapproved protocol interface" .-> CHAIN

    classDef safe fill:#e7f2e9,color:#184a30,stroke:#8cb89b
    classDef research fill:#eaf0ff,color:#203e74,stroke:#8aa3d6
    classDef blocked fill:#fff1da,color:#6a4619,stroke:#d5aa6e
    class CHAIN,SCAN,STATE safe
    class P,UI,SIGN,PSBT,NET,C research
    class STORE,SHIELD,VERIFIER blocked
~~~

The diagram is a **module dependency model**, not proof that every arrow has a production implementation.

| Layer | Source or design reference | Evidence / status |
| --- | --- | --- |
| WSP-1 | [WSP specification](../../wsp/wsp-1/SPEC.md); [separate WSP repository](https://github.com/Urriki1502/wam-silent-payments) | Regtest and historical WSP profile; maintainer adoption pending |
| Wallet/signer foundation | [Architecture](../../ARCHITECTURE.md); [Phase 12 adapters](../PHASE12-REAL-ADAPTERS.md) | V1 internal testing only |
| V2 local policy | [V2 scope](https://github.com/Urriki1502/wam-privacy/blob/v2/research-freeze-2026-10-09/docs/v2/IMPLEMENTATION-SCOPE.md); [PR #52](https://github.com/Urriki1502/wam-privacy/pull/52) | Scoped grants, revocation and deny-by-default fixtures |
| Disclosure | [PR #53](https://github.com/Urriki1502/wam-privacy/pull/53) | Local projection; trusted UI still required |
| Relay | [PR #54](https://github.com/Urriki1502/wam-privacy/pull/54) | Offline routing and observer simulator |
| Integration bridge | [PR #55](https://github.com/Urriki1502/wam-privacy/pull/55) | Frozen V1 and WSP test contracts |
| Durable capability state | [SEC-001 PR #70](https://github.com/Urriki1502/wam-privacy/pull/70) | Hardware-independent test witness is not a production authority |
| Signer replay control | [SEC-002 PR #67](https://github.com/Urriki1502/wam-privacy/pull/67) | Local journal; recovery identity and external state remain open |
| Multi-store composition | [SEC-003 PR #71](https://github.com/Urriki1502/wam-privacy/pull/71) | Conservative failure handling; no distributed ACID claim |
| Trusted authorization | [AUTH-001 PR #69](https://github.com/Urriki1502/wam-privacy/pull/69) | Synthetic consent boundary, not a wallet UI audit |
| Shielded tree/consensus | [CORE-003 PR #61](https://github.com/Urriki1502/wam-privacy/pull/61) | Design proposal; no WAM Core rule change |

## Branch topology and review links

~~~mermaid
flowchart TD
    A["main · V1"] --> B["v2/research-base · #52"]
    B --> D2["v2/02-selective-disclosure · #53"]
    D2 --> D3["v2/03-relay-metadata-simulator · #54"]
    D3 --> D4["v2/04-v1-regression-bridge · #55"]
    D4 --> D5["v2/05-qualification-handoff · #56"]
    D5 --> F["v2/research-freeze-2026-10-09"]
    F --> SA["SEC-001 · #70"]
    F --> SB["SEC-002 · #67"]
    F --> SC["SEC-003 · #71"]
    F --> AU["AUTH-001 · #69"]
    F --> E["P0 E · #68"]
    F --> R1["CORE-003 step 01 · #58"]
    R1 --> R2["step 02 · #59"]
    R2 --> R3["step 03 · #60"]
    R3 --> R4["step 04 · #61"]
    SA -. "pinned interface" .-> SC
    SB -. "pinned interface" .-> SC
    SA -. "independent test" .-> E
    SB -. "independent test" .-> E
    SC -. "independent test" .-> E
    AU -. "independent test" .-> E
    classDef f fill:#def0e4,color:#183a26,stroke:#75a88a
    classDef w fill:#e6ecff,color:#243a70,stroke:#8aa0d4
    classDef p fill:#fff0da,color:#694819,stroke:#d5a569
    class A,F f
    class B,D2,D3,D4,D5,R1,R2,R3,R4 w
    class SA,SB,SC,AU,E p
~~~

### Navigate the actual GitHub branches

| Scope | Branch and PR | Relationship |
| --- | --- | --- |
| Stable default | [main](https://github.com/Urriki1502/wam-privacy/tree/main) | Published V1 foundation; separate from draft V2 |
| V1 source identity | [95dfe0ab snapshot](https://github.com/Urriki1502/wam-privacy/commit/95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127) | Immutable qualifying reference |
| V2 research sequence | [#52](https://github.com/Urriki1502/wam-privacy/pull/52) → [#53](https://github.com/Urriki1502/wam-privacy/pull/53) → [#54](https://github.com/Urriki1502/wam-privacy/pull/54) → [#55](https://github.com/Urriki1502/wam-privacy/pull/55) → [#56](https://github.com/Urriki1502/wam-privacy/pull/56) | Draft stacked research |
| V2 original snapshot | [5af86cfd commit](https://github.com/Urriki1502/wam-privacy/commit/5af86cfd5be27a3275079cbccde2abd2366ebb2b) | Historic qualification source before docs refresh |
| V2 documentation branch | [research freeze ref](https://github.com/Urriki1502/wam-privacy/tree/v2/research-freeze-2026-10-09) | Fast-forward documentation update, new SHA needs new qualification |
| Security A | [SEC-001 #70](https://github.com/Urriki1502/wam-privacy/pull/70) | Durable policy reference |
| Security B | [SEC-002 #67](https://github.com/Urriki1502/wam-privacy/pull/67) | Persistent signer journal |
| Security C | [SEC-003 #71](https://github.com/Urriki1502/wam-privacy/pull/71) | Pinned A/B composition, **not** A/B merged |
| Trusted authorization | [AUTH-001 #69](https://github.com/Urriki1502/wam-privacy/pull/69) | Synthetic boundary review |
| Independent matrix | [P0 E #68](https://github.com/Urriki1502/wam-privacy/pull/68) | Pinned A/B/C/D evidence, not production acceptance |
| Core research | [#58](https://github.com/Urriki1502/wam-privacy/pull/58) → [#59](https://github.com/Urriki1502/wam-privacy/pull/59) → [#60](https://github.com/Urriki1502/wam-privacy/pull/60) → [#61](https://github.com/Urriki1502/wam-privacy/pull/61) | Four-step proposal chain; Core remains unchanged |

**Solid arrows** depict the actual PR base relationship; **dotted arrows** depict read-only/pinned research test dependencies, not Git merges.

## Integration and acceptance gates

~~~mermaid
flowchart TD
    CODE["Research implementation"] --> TEST["Local deterministic tests"]
    TEST --> PIN["Exact source SHA + CI artifacts"]
    PIN --> REVIEW["Independent security reviews"]
    REVIEW --> OPS["Operator/testnet validation"]
    OPS --> DECISION{"Maintainer protocol approval?"}
    DECISION -->|No or pending| HOLD["Remain research-only"]
    DECISION -->|Approved with activation plan| RELEASE["Separate release process"]
    classDef pending fill:#fff2de,color:#5a3c17,stroke:#d8aa62
    class HOLD,REVIEW,OPS,DECISION pending
~~~

| Gate | Status | Missing dependency |
| --- | --- | --- |
| V1 internal qualification | Historical tests and reports available | No independent external Phase 15C/D signoff |
| V2 and pinned P0 regression | Synthetic evidence and reproducible test runners available | CI must be reverified for every new source/PR-base head |
| Policy rollback authority | Reference witness contract | Hardware or remote trusted monotonic store |
| Signer and cross-store durability | Fail-closed reference cases | Authenticated signer binding, crash recovery and multi-store consistency |
| User approval / disclosure | Local fixtures | Real trusted UI provenance, user-facing metadata and FFI lifecycle |
| Shielded Core integration | Four proposal steps | Canonical root, anchor, reorg and activation rule decisions |
| Release and mainnet | **Not authorized** | External audit, operator history, approvals and release procedure |

For the authoritative review list, use [Issue #66](https://github.com/Urriki1502/wam-privacy/issues/66). For consensus-sensitive design questions, see [Issue #57](https://github.com/Urriki1502/wam-privacy/issues/57).

## Reviewer workflow

1. **Confirm scope and snapshot.** Record the exact branch HEAD, original V1/V2 baseline pins, Core dependency and reviewer identity.
2. **Inspect safety properties.** Confirm denial, revocation, restart, reorg, replay, malformed input and uncertainty cases; independently exercise negative vectors.
3. **Reproduce evidence.** Run [V2-05 workflow](https://github.com/Urriki1502/wam-privacy/actions/workflows/v2-05-qualification.yml) or pin local tests to the documented commit, then compare artifacts. Treat stale runs as historical.
4. **Separate wallet and consensus decisions.** Wallet-local control does not authorize new state-root or nullifier acceptance rules in Core.
5. **Issue a disposition.** Record accept-design / changes-requested / blocked along with exact SHA, findings, action owner, and retest criteria.

## Reproducibility and provenance

Original documented source points:

| Snapshot | Commit | Meaning |
| --- | --- | --- |
| V1 logical baseline | [95dfe0ab](https://github.com/Urriki1502/wam-privacy/commit/95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127) | Frozen experimental V1 source |
| V2 pre-refresh snapshot | [5af86cfd](https://github.com/Urriki1502/wam-privacy/commit/5af86cfd5be27a3275079cbccde2abd2366ebb2b) | Original V2 researched source |
| Evidence track | [P0 E #68](https://github.com/Urriki1502/wam-privacy/pull/68) | Independent pinned-lane qualification |
| Core security finding | [WAM Security #18](https://github.com/Urriki1502/wam-security/pull/18) | Separate upstream pool race diagnosis; not Core consensus bypass |

This project guide and README are **documentation-only revisions**. They do not change any executable model, circuit, signer, RPC, consensus rule or protected test. Moving a freeze branch pointer makes its new HEAD a **different commit**: historical green test reports apply only to their recorded SHAs and may not be reused as certification of the documentation successor.

[← Back to WAM Privacy README](../../README.md) · [Security policy](../../SECURITY.md) · [License](../../LICENSE)
