# WAM Privacy

Research, specifications, prototypes, and validation for privacy technologies proposed for WAM.

> **Status:** Research / Prototype  
> **Mainnet:** No mainnet integration is implied by this repository.  
> **Consensus:** No consensus change is implied unless a future proposal is separately specified, reviewed, tested, and accepted by WAM maintainers.

## Mission

Build a privacy stack for WAM by adapting well-studied ideas from mature privacy and Bitcoin ecosystems without blindly cloning another chain.

The project prioritizes:

- privacy without sacrificing monetary-policy auditability;
- separation of scanning authority and spending authority;
- standard cryptographic constructions over custom cryptography;
- testable security invariants;
- fail-closed behavior at trust boundaries;
- incremental deployment with explicit review gates;
- reuse of already-qualified WAM privacy work instead of unnecessary reimplementation.

## Existing WSP-1 baseline

WAM already has a substantial Silent Payments qualification implementation in:

- `Urriki1502/wam-silent-payments`
- branch: `feat/wsp1-v1.0`
- package status: `1.0.0.dev0`
- previously qualified node profile: WAM Core v0.1.11 / regtest

That repository already contains BIP-352 derivation, durable scanning, recovery, PSBTv2 signing, adversarial tests, deep reorg tests, differential tests and fuzz evidence.

Therefore this repository does **not** restart WSP-1 from zero. Its first implementation task is to adopt, review and requalify that baseline against current WAM Core.

See [docs/EXISTING-ASSETS.md](docs/EXISTING-ASSETS.md) and [docs/WAM-CORE-COMPATIBILITY.md](docs/WAM-CORE-COMPATIBILITY.md).

## Current engineering status

| Phase | Status |
| --- | --- |
| Phase 0 — Architecture / threat model | **MERGED** |
| Phase 1 — WSP-1 / current-Core requalification | **INTERNAL ENGINEERING PASS** |
| Phase 2 — Privacy-aware wallet policy | **INTERNAL ENGINEERING PASS** |
| Phase 3 — Signer abstraction | **INTERNAL ENGINEERING PASS** |
| Phase 4 — PayJoin safety | **INTERNAL ENGINEERING PASS** |
| Phase 5 — Network privacy policy | **INTERNAL ENGINEERING PASS** |
| Phase 6 — Stack integration contract | **INTERNAL ENGINEERING PASS** |
| Phase 7 — Shielded state model | **INTERNAL ENGINEERING PASS** |
| Phase 8 — Isolated Halo2 prototype | **INTERNAL ENGINEERING PASS** |
| Phase 9A–9C — Integrated shielded action | **INTERNAL ENGINEERING PASS** |
| Phase 10A–10C — Bundle + serialization | **INTERNAL ENGINEERING PASS** |
| Phase 10D — Protocol hardening/context binding | **INTERNAL ENGINEERING PASS** |
| Phase 11 — Key hierarchy + HPKE note encryption | **INTERNAL ENGINEERING PASS** |
| Phase 12A — Real WAM/WSP adapters | **INTERNAL ENGINEERING PASS** |
| Phase 12B — Shielded wallet state/recovery | **INTERNAL ENGINEERING PASS** |
| Phase 13A — Core-facing Halo2 verifier C ABI | **INTERNAL ENGINEERING PASS** |
| Phase 13B–13D — Core regtest/state/resource integration | **INTERNAL ENGINEERING PASS** |
| Phase 14A — Reproducible release identity | **UNDER QUALIFICATION** |
| Phase 14B–14D — Fuzz/performance/release hardening | **PENDING** |
| Phase 15 — Independent review/testnet/handoff | **PENDING** |

An internal engineering PASS is not a production-readiness, anonymity, audit, or mainnet claim.

## Initial research tracks

1. **WSP-1 — Silent Payments adoption / requalification**
   - BIP-352-derived static payment addressing;
   - receiver scanning;
   - scan/spend authority separation;
   - deterministic recovery and rescan behavior;
   - qualification of the existing WSP implementation against current WAM Core.

2. **Wallet privacy**
   - privacy-aware coin selection;
   - change and transaction fingerprint reduction;
   - metadata minimization.

3. **Signer architecture**
   - software signer;
   - offline signer;
   - future hardware-backed signer through one interface.

4. **PayJoin**
   - BIP-78 compatibility research;
   - BIP-77 asynchronous PayJoin research;
   - no custodial mixer design.

5. **Network privacy**
   - broadcast privacy;
   - RPC isolation;
   - optional privacy transports.

6. **Shielded research**
   - Zcash Orchard / Halo 2 as research references;
   - note commitments, nullifiers, viewing capabilities, value conservation;
   - research only until formal protocol, test vectors, independent review, and testnet validation exist.

## Repository map

- [ARCHITECTURE.md](ARCHITECTURE.md) — system layers and trust boundaries.
- [THREAT-MODEL.md](THREAT-MODEL.md) — assets, attackers, security goals, and invariants.
- [SECURITY.md](SECURITY.md) — disclosure and research-safety policy.
- [docs/DESIGN-PRINCIPLES.md](docs/DESIGN-PRINCIPLES.md) — engineering rules.
- [docs/PRIVACY-ROADMAP.md](docs/PRIVACY-ROADMAP.md) — staged delivery gates.
- [docs/REFERENCES.md](docs/REFERENCES.md) — upstream standards and research references.
- [docs/EXISTING-ASSETS.md](docs/EXISTING-ASSETS.md) — reusable work already completed.
- [docs/WAM-CORE-COMPATIBILITY.md](docs/WAM-CORE-COMPATIBILITY.md) — current Core qualification target.
- [wsp/wsp-1/SPEC.md](wsp/wsp-1/SPEC.md) — WSP-1 architecture/profile contract.
- [docs/SHIELDED-PROTOCOL-MODEL.md](docs/SHIELDED-PROTOCOL-MODEL.md) — Phase 7 shielded state semantics.
- [docs/SHIELDED-REVIEW-PLAN.md](docs/SHIELDED-REVIEW-PLAN.md) — external review gates for shielded work.
- [qualification/PHASE7-STATUS.md](qualification/PHASE7-STATUS.md) — Phase 7 qualification status.
- [docs/ZK-PROTOTYPE.md](docs/ZK-PROTOTYPE.md) — Phase 8 Halo2 prototype stages and non-claims.
- [qualification/PHASE8-STATUS.md](qualification/PHASE8-STATUS.md) — Phase 8 internal qualification status.
- [docs/PHASE9C-VALUE-ACTION.md](docs/PHASE9C-VALUE-ACTION.md) — Phase 9C integrated value-action relation.
- [qualification/PHASE9-STATUS.md](qualification/PHASE9-STATUS.md) — Phase 9 qualification status.
- [docs/PHASE10C-SERIALIZATION.md](docs/PHASE10C-SERIALIZATION.md) — Phase 10C canonical research envelope/verifier contract.
- [qualification/PHASE10-STATUS.md](qualification/PHASE10-STATUS.md) — Phase 10 qualification status.

## Development rule

Every implementation phase must define, before code is promoted:

```
scope
→ threat model
→ trust boundary
→ test environment
→ security invariants
→ exit criteria
```

If an invariant cannot be tested, it is not considered complete.

## License

MIT. See [LICENSE](LICENSE).
