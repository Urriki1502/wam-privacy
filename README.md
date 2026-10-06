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
- incremental deployment with explicit review gates.

## Initial research tracks

1. **WSP-1 — Silent Payments research**
   - BIP-352-derived static payment addressing;
   - receiver scanning;
   - scan/spend authority separation;
   - deterministic recovery and rescan behavior.

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
- [wsp/wsp-1/SPEC.md](wsp/wsp-1/SPEC.md) — WSP-1 design skeleton.

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
