# WAM Privacy V2 — Locked Implementation Scope

Status: implementation planning only; no production or activation claim.
Base V1 source: `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127`.
Design reference: draft PR #50 (`docs/v2/ARCHITECTURE-THREAT-MODEL.md`, `ACCEPTANCE-TEST-MATRIX.md`, `MAINTAINER-COMPATIBILITY.md`). This branch is independent; PR #50 is not authorized for merge by this document.

## Five pillars only

1. Information-flow policy: explicit data labels, actor-to-data allowlist, default deny, no secret-bearing logs.
2. Capability model: independently enforce SCAN, VIEW, SIGN, BROADCAST, DISCLOSE, AUDIT; no implicit privilege inheritance; scoped, versioned, expiring grants and revocation.
3. Selective disclosure: wallet-local user-authorized projection of only selected facts, scoped to account/resource/purpose; no unsupported ZK disclosure claims.
4. Privacy relay: separate broadcast routing policy from proof/consensus validation; simulate failures first, no private-route-to-clearnet silent fallback; live network integration needs maintainer confirmation.
5. Metadata isolation: account for IP, timing, first-relay, RPC and counterparty correlation; specify observer and residual leakage, test with synthetic local traces.

## Implementation sequence

- V2-01: implement deterministic, bounded policy parser/evaluator and capability enforcement in standalone wallet/application-layer code; acceptance CAP-001..010 and FLOW-001..006.
- V2-02: implement narrow local disclosure projection and redacted decision events; acceptance FLOW-003..006, PERF-001..002.
- V2-03: implement route policy simulator and metadata observer fixtures, with no live relay integration; acceptance NET-001..004.
- V2-04: integration/regression bridge against pinned V1, including restart/reorg and trust-boundary negative tests; acceptance FLOW-007..008, CORE-001..003, COMPAT-001..002.
- V2-05: clean-clone evidence, full acceptance matrix, residual-risk report and maintainer review package. External independent reviews are not self-certified.

## Existing V1 limitations: explicitly tracked, not silently fixed

- Experimental CoreShieldedState next_anchor input remains untrusted for production; canonical tree-root derivation and verified Core transition connection require a separate Core architecture decision.
- Research Merkle depth, generated regtest-only Core hook and disabled-by-default integration remain limitations.
- Phase 15C/15D external review, Phase 15E findings remediation, operator testnet history and Phase 15F maintainer handoff remain pending as documented.
- No V1 implementation, circuit, verifier, Core consensus, protocol identity, key format, release tag or activation changes are authorized by this plan.

## Non-waivable gates

Every implementation PR must identify exact head SHA, deterministic positive/negative fixtures, required CI results and affected trust boundaries. Preserve V1 source-drift and cryptographic/state-integrity gates; V2-only checks must be isolated without disabling V1 controls. No merge on unresolved P0, missing required evidence or unknown compatibility. Maintainer confirmation is required before live relay integration, proof-backed disclosure, key-profile changes or production Core work.
