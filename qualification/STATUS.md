# Phase 1 Status

| Gate | Status | Evidence |
| --- | --- | --- |
| WSP source pin | PASS (pin established) | `dcf1aecc00a64bfad3151fa202c3e07d47d83e69` — macOS PTY isolation fix merged |
| WAM Core target pin | PASS (pin established) | `260bc468e5adffea7ce68d8f97fac3e27e4c50b2` |
| WSP upstream fix CI | PASS (internal engineering) | PR #8; runs `37463840923` and `37463840992` both successful; self-test 151/151 |
| WSP contract / self-test in wam-privacy | PENDING REPIN VALIDATION | Phase 1 contract workflow will rerun against `dcf1aecc...` |
| Core guarded-source drift | PASS (internal engineering) | run `37458974176`; artifact digest `sha256:d64d417885971363cc6a938b588c0ef0eebb5e000eb4ea71a98e7b9a8817c34b` |
| Current-Core isolated regtest integration | PENDING | rerun on macOS against the repinned WSP commit and the already-built target daemon |
| Deep reorg rerun on current Core | PENDING | isolated two-node qualification |
| Independent security review | BLOCKED — external review/adoption | external decision |
| Mainnet/testnet WSP profile adoption | BLOCKED — external review/adoption | maintainer decision |

## Current claim

`WSP-1 PTY FIX MERGED — REPIN VALIDATION / CURRENT-CORE REGTEST REQUALIFICATION PENDING`

The macOS failure observed at WSP-E2E-003 was traced to the offline-signer PTY harness and fixed without changing cryptography, protocol, wallet, or consensus behavior.

No production-readiness claim is made by this status file.
