# Phase 1 Status

| Gate | Status | Evidence |
| --- | --- | --- |
| WSP source pin | PASS (pin established) | `dcf1aecc00a64bfad3151fa202c3e07d47d83e69` — macOS PTY isolation fix merged |
| WAM Core target pin | PASS (pin established) | `260bc468e5adffea7ce68d8f97fac3e27e4c50b2` |
| WSP upstream fix CI | PASS (internal engineering) | PR #8; runs `37463840923` and `37463840992`; self-test 151/151 |
| WSP contract / self-test in wam-privacy | PASS (internal engineering) | run `37557003726`; artifact digest `sha256:bedbf1f97720966a292aed8b8dec86a44de67ce52c31645a17e5764407c95bcc` |
| Core guarded-source drift | PASS (internal engineering) | run `37557004861`; artifact digest `sha256:dc7cdb774ff1a82eb46426c07b0fb6e24f6898e1349cdf7932056b30ad9c6bce` |
| Current-Core isolated regtest integration | **PASS (internal engineering)** | macOS arm64 Gate C; WSP-E2E-001..007 all pass |
| Deep reorg rerun on current Core | **PASS (internal engineering)** | real reorg depths 1 / 12 / 100 / 300 all pass |
| Interop suite | **PASS (internal engineering)** | SP2-001..SP2-010 all pass |
| Regtest suite | **PASS (internal engineering)** | SPREG-001..SPREG-009 all pass |
| Independent security review | BLOCKED — external review/adoption | external decision |
| Mainnet/testnet WSP profile adoption | BLOCKED — external review/adoption | maintainer decision |

## Current claim

`PHASE 1 INTERNAL ENGINEERING PASS — CURRENT WAM CORE REQUALIFIED ON ISOLATED macOS ARM64 REGTEST`

Pinned runtime qualification:

- WSP: `dcf1aecc00a64bfad3151fa202c3e07d47d83e69`
- WAM Core: `260bc468e5adffea7ce68d8f97fac3e27e4c50b2`
- `wamd` SHA-256: `99a5f20fb741620de3655fcab980b3303d8caa2bbb6025dc490eb8cca4074a34`
- platform: macOS arm64
- final Gate C result: **PASS**

This is an internal engineering qualification result. It is not an external audit, production-readiness, anonymity, consensus-activation, or mainnet-adoption claim.
