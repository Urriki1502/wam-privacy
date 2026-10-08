# V2 Compatibility Gate — WAM Maintainer Intent

**Document status:** internal interpretation of the current `docs/DESIGN-PRINCIPLES.md`, `THREAT-MODEL.md`, `docs/PRIVACY-ROADMAP.md` and Phase 13–15 gates. This is not maintainer approval.

## Non-negotiable baseline

1. Keep 22M fixed WAM supply, existing atomic-unit scale and verifiable value conservation.
2. Do not weaken spend-key isolation, nullifier uniqueness or fail-closed proof/serialization checks.
3. Stay on application/wallet layers before proposing any Core/consensus-sensitive design.
4. Keep Core integration experimental and regtest-only unless reviewed and explicitly adopted.
5. Support deterministic recovery, rollback/replay under reorgs and independent signer validation.
6. Use proven crypto primitives, not novel construction for marketing differentiation.
7. Make observer/assumptions/remaining leakages explicit; avoid unconditional anonymity claims.
8. Preserve protocol/circuit/VK identity discipline and reproducible regression evidence.

## Proposed feature map

| V2 feature | WAM objective | Preserved invariant | Differentiator | Current disposition |
| --- | --- | --- | --- | --- |
| SCAN/VIEW/SIGN/BROADCAST/AUDIT capability boundaries | least secret / signer independence | spend isolation, recovery | end-to-end least-privilege data flow | DESIGN COMPATIBLE, implementation after freeze |
| Purpose-bound DISCLOSE projection | controllable observation, no spend access | view does not confer spend | user-scoped privacy boundary | DESIGN COMPATIBLE for local export |
| Policy evaluation + redacted audit | fail closed, measurable privacy | untrusted callers cannot sign | testable privacy accountability | DESIGN COMPATIBLE, implementation after freeze |
| Separate broadcast endpoint/policy | metadata leakage control | signing independent from transport | lower endpoint role correlation | DESIGN COMPATIBLE for policy-only simulation |
| Live privacy relay integration | origin metadata reduction | node/decentralization expectations | optional route isolation | NEEDS_MAINTAINER_CONFIRMATION for WAM runtime |
| Cryptographic disclosure proof | narrow viewing access | protocol/version/VK compatibility | verifiable limited attestations | NEEDS_MAINTAINER_CONFIRMATION and independent crypto review |
| On-chain disclosure/consensus field | privacy accounting | all consensus/state invariants | uncertain | DO NOT IMPLEMENT without maintainer approval |
| Production tree/next_anchor integration | canonical state safety | Merkle/nullifier/solvency | essential security prerequisite | BLOCKED pending explicit Core architecture decision |

## Maintainer review package once V2 matures

For each proposed integration change: explain the user threat, exact affected module and Core interface, protocol-impact classification (none/wallet-only/consensus), source and evidence links, attack/failure cases, resource cost, backward compatibility, rollback strategy, residual limitations, and a narrowly phrased maintainer decision request.

No maintainer conversation or approval is inferred from internal documents. If the current upstream WAM implementation differs from the repository's pin, re-run compatibility analysis before implementation/merge.
