<div align="center">

# WAM Privacy

### Privacy research • Wallet security • Reproducible validation

**A modular research stack for privacy capabilities in WAM — from address scanning and wallet controls to shielded-state experiments.**

![Scope](https://img.shields.io/badge/scope-research%20%26%20regtest-244765)
![V1](https://img.shields.io/badge/V1-internal%20qualification-307b65)
![V2](https://img.shields.io/badge/V2-review%20branches-3269a8)
![Mainnet](https://img.shields.io/badge/mainnet-not%20approved-916142)
![License](https://img.shields.io/badge/license-MIT-424a59)

[**Architecture**](#architecture-at-a-glance) · [**Research tracks**](#research-tracks) · [**Branch map**](#branch-and-review-map) · [**Evidence**](#verification-and-evidence) · [**Maintainer guide**](docs/v2/PROJECT-GUIDE.md)

</div>

---

> [!IMPORTANT]
> **Research and prototype only.** This repository does **not** ship a WAM mainnet privacy upgrade, enable a consensus rule, demonstrate production anonymity, or provide an independent cryptographic audit. All integration and release decisions remain with WAM maintainers.

## What this repository does

WAM Privacy brings together multiple privacy and security research tracks under one verifiable, layered design. The objective is to improve privacy **without confusing wallet behavior with blockchain consensus**, and without relaxing value conservation, spend authority, or recovery requirements.

| Research area | Engineering focus | Current boundary |
| :--- | :--- | :--- |
| **Address privacy** | WSP-1 / Silent Payments, receiver scanning, deterministic recovery | Prior WSP implementation; WAM adoption still requires review |
| **Transaction privacy** | PayJoin policy, proposal validation, signing constraints | Local models and regtest evidence |
| **Wallet privacy** | Scoped capabilities, consent, disclosure, signer isolation | V1/V2 research; trusted hardware/UI still required |
| **Network privacy** | Relay choices, metadata observability, safe routing failures | Simulator; no live anonymity claim |
| **Shielded research** | Halo2, commitments, nullifiers, value conservation, reorg recovery | Experimental; **no Core activation** |

### Design principles

**Fail closed** at uncertain boundaries · **Separate scan and spend authority** · **Bind all decisions to exact contexts** · **Pin and reproduce evidence** · **Never equate green CI with deployment approval**

## Architecture at a glance

~~~mermaid
flowchart LR
    CORE["WAM Core / chain history"] --> SCAN["WSP-1 scanner"]
    SCAN --> WALLET["Wallet state + recovery"]
    WALLET --> POLICY["V2 capability policy"]
    POLICY --> CONSENT["Trusted consent boundary"]
    CONSENT --> SIGNER["V1 signer / PSBT"]
    SIGNER --> TX["Transaction construction / PayJoin"]
    TX --> RELAY["Broadcast policy / relay"]
    WALLET -. "research state inputs" .-> SHIELD["Shielded notes / commitments"]
    SHIELD --> PROOFS["Halo2 proof + verifier model"]
    PROOFS -. "proposal only · Core review required" .-> CORE

    classDef chain fill:#24364b,color:#fff,stroke:#536b84
    classDef wallet fill:#e8f4ff,color:#123a60,stroke:#92badb
    classDef research fill:#fff2df,color:#644317,stroke:#d4ad70
    class CORE chain
    class SCAN,WALLET,POLICY,CONSENT,SIGNER,TX,RELAY wallet
    class SHIELD,PROOFS research
~~~

**Trust boundary:** observing payments must not grant spending authority. Research proof verification is **not** equivalent to a WAM consensus rule. See [architecture](ARCHITECTURE.md), [threat model](THREAT-MODEL.md), and the [detailed dependency map](docs/v2/PROJECT-GUIDE.md#system-dependencies).

## Research tracks

| Track | Implemented / evidenced | Still required |
| :--- | :--- | :--- |
| **V1 · Foundation** | Wallet/signer models, Halo2 experiments, verification and regtest suites, Phase 15 internal review package | External Phase 15C/D reviews, operator evidence, maintainer approval |
| **V2 · Wallet controls** | Policy, selective disclosure, relay simulation, V1 bridge, 29-case evidence classifications | Real trusted UI/storage, long-lived integration and broader testing |
| **SEC-001/002/003** | Durable policy, signer journal, conservative multi-store composition tests | Trusted anti-rollback service, signer identity/reconciliation, distributed recovery design |
| **AUTH-001** | Local consent/disclosure guard and adversarial fixtures | Actual wallet UI ownership and C++ FFI lifetime review |
| **P0 E** | Pinned A/B/C/D regression and reproducibility evidence | New-head CI qualification, external review, production dependencies |
| **CORE-003** | Canonical-root model, differential vectors, reorg journal, proposed Core interface | Maintainer protocol decisions and consensus-sensitive implementation review |

The detailed state of each gate lives in [V2 review notes](https://github.com/Urriki1502/wam-privacy/blob/v2/research-freeze-2026-10-09/docs/v2/V2-05-REVIEW-HANDOFF.md), the [Phase 15 review plan](docs/SHIELDED-REVIEW-PLAN.md), and [Issue #66](https://github.com/Urriki1502/wam-privacy/issues/66).

## Branch and review map

Research branches are **separate proposals**, not features merged into main.

~~~mermaid
flowchart TD
    MAIN["main · V1 baseline"] --> V201["V2-01 · PR #52"]
    V201 --> V202["V2-02 · PR #53"]
    V202 --> V203["V2-03 · PR #54"]
    V203 --> V204["V2-04 · PR #55"]
    V204 --> V205["V2-05 · PR #56"]
    V205 --> FREEZE["V2 research freeze · original 5af86cfd"]
    FREEZE --> SEC["SEC-001 / 002 / 003"]
    FREEZE --> AUTH["AUTH-001"]
    FREEZE --> P0["P0 E · evidence matrix"]
    FREEZE --> C1["CORE-003 · step 01"]
    C1 --> C2["step 02"]
    C2 --> C3["step 03"]
    C3 --> C4["step 04"]

    classDef stable fill:#e5eee9,stroke:#65957b,color:#213c2b
    classDef pending fill:#eaf0ff,stroke:#7896cd,color:#233e71
    classDef open fill:#fff2df,stroke:#d3a464,color:#65471f
    class MAIN,FREEZE stable
    class V201,V202,V203,V204,V205,C1,C2,C3,C4 pending
    class SEC,AUTH,P0 open
~~~

Full clickable branches, PR dependencies, frozen SHA provenance and owner decisions: **[Project guide →](docs/v2/PROJECT-GUIDE.md#branch-topology-and-review-links)**.

## Verification and evidence

Internal workflow success establishes **only the checks actually exercised at their exact source SHAs**.

- **V1:** [Phase 15 status](qualification/PHASE15-STATUS.md), [state-machine review intake](reviews/PHASE15C-STATE-MACHINE-REVIEW.md), [cryptography review intake](reviews/PHASE15D-CRYPTO-CIRCUIT-REVIEW.md).
- **V2:** [29-case qualification handoff](https://github.com/Urriki1502/wam-privacy/blob/v2/research-freeze-2026-10-09/docs/v2/V2-05-REVIEW-HANDOFF.md), [acceptance matrix](https://github.com/Urriki1502/wam-privacy/blob/v2/research-freeze-2026-10-09/v2/acceptance_matrix.json), [CI workflow](https://github.com/Urriki1502/wam-privacy/blob/v2/research-freeze-2026-10-09/.github/workflows/v2-05-qualification.yml).
- **P0 research:** [SEC-001](https://github.com/Urriki1502/wam-privacy/pull/70) · [SEC-002](https://github.com/Urriki1502/wam-privacy/pull/67) · [SEC-003](https://github.com/Urriki1502/wam-privacy/pull/71) · [AUTH-001](https://github.com/Urriki1502/wam-privacy/pull/69) · [P0 E](https://github.com/Urriki1502/wam-privacy/pull/68).
- **Core design:** [CORE-003 steps 01–04](https://github.com/Urriki1502/wam-privacy/pull/61) and [maintainer decision record](https://github.com/Urriki1502/wam-privacy/issues/57).
- **Current pool finding:** [WS-POOL-JOB-001 deterministic reproduction](https://github.com/Urriki1502/wam-security/pull/18) is **a separate WAM Security issue**, not an accepted privacy feature.

### Release gates that remain open

Trusted monotonic storage · real signer identity and crash reconciliation · authenticated wallet consent/UI · FFI lifetime qualification · Phase 15C/15D attributed external review · operator testnet history · Core consensus decisions · WSP-1 deployment profile.

## Repository and related projects

| Resource | Purpose |
| :--- | :--- |
| [Project guide](docs/v2/PROJECT-GUIDE.md) | Clickable module map, branch structure, diagrams and reviewer workflow |
| [Architecture](ARCHITECTURE.md) / [Threat model](THREAT-MODEL.md) | Layering, assets, attackers and invariants |
| [WSP-1 specification](wsp/wsp-1/SPEC.md) | Silent Payments research interface |
| [WAM Silent Payments](https://github.com/Urriki1502/wam-silent-payments) | Prior WSP-1 scanner/signer implementation |
| [WAM Silent Wallet](https://github.com/Urriki1502/wam-silent-wallet) | Independent wallet prototype |
| [WAM Security](https://github.com/Urriki1502/wam-security) | Pool, payout, Redis and broader security regression tracks |
| [WAM Core](https://github.com/wamcoin-core-dev/wam-coin) | Upstream consensus and node authority |

## For maintainers

Start with the [project guide](docs/v2/PROJECT-GUIDE.md), inspect the pinned source and negative tests, then respond to the architecture and security decisions linked there. **No research branch is an implicit merge request for production deployment.**

> **Source provenance:** V1 logical baseline [95dfe0ab](https://github.com/Urriki1502/wam-privacy/commit/95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127); V2 pre-documentation snapshot [5af86cfd](https://github.com/Urriki1502/wam-privacy/commit/5af86cfd5be27a3275079cbccde2abd2366ebb2b). Documentation refreshes do not retroactively qualify the newer commit.

[Security policy](SECURITY.md) · [License](LICENSE) · [Research roadmap](docs/PRIVACY-ROADMAP.md)
