# Phase 15 Status

**Scope:** final project-owned review/testnet/handoff gate before any activation decision.

| Stage | Status | Evidence |
| --- | --- | --- |
| 15A — external-review / handoff package freeze | **LEGACY PASS — corrected candidate REQUALIFICATION IN PROGRESS** | run `37629367529`; artifact digest `sha256:bf80b30c36478f2b03d40e8be19166d8d075c56f048e3303138821444c4eab49`; merge `e5d436a201d3fdf26f2a6bb2ea750be8ce213aab` |
| 15B — extended regtest/testnet drill harness | **LEGACY PASS — corrected candidate REQUALIFICATION IN PROGRESS** | run `37634670000`; artifact digest `sha256:60c7ed387a4d5d47778257806359add698100e6df52581a08fc040ea8a5b3e47`; merge `d50e0c18b65734aa160df8b38b80f7f243160316` |
| 15C — independent state-machine review | **READY FOR EXTERNAL REVIEW** | reviewer intake package + issue required |
| 15D — independent cryptographic/circuit review | **READY FOR EXTERNAL REVIEW** | reviewer intake package + issue required |
| 15E — remediation closure | **PENDING EXTERNAL FINDINGS** | confirmed findings require fixes + regression evidence |
| 15F — maintainer handoff | **PENDING** | exact review/testnet evidence + maintainer decision |

## Candidate baseline

The previous internal hardening baseline `00f8065c4f7b48fec01e4d97626ecbf2cc125852` was **superseded**
by P0 remediation (Halo2 domain-separator constraints and Core verified-transition
trust boundary). Its earlier Phase 15A/15B PASS artifacts apply only to that
legacy source candidate.

**Current corrected source candidate (internal requalification):**

`8bfbced65299a8491345b54b38bff0db498b618d`

Phase 14A/B/C/D gates have passed on this exact candidate (see
`qualification/PHASE14-STATUS.md`). The corrected Phase 15A review
package and Phase 15B drill must be regenerated and PASS on the
current source candidate; neither historical Phase 15 result qualifies
the new candidate automatically.

No later circuit/protocol/wallet/verifier/Core-integration source edits
are permitted without selecting and requalifying another new baseline.

## Phase 15A evidence

- workflow run: `37629367529`;
- artifact: `phase15a-review-handoff-package`;
- artifact digest: `sha256:bf80b30c36478f2b03d40e8be19166d8d075c56f048e3303138821444c4eab49`;
- merge commit: `e5d436a201d3fdf26f2a6bb2ea750be8ce213aab`;
- result: **PASS_REVIEW_PACKAGE_READY**.

## Phase 15B evidence

- workflow run: `37634670000`;
- artifact: `phase15b-extended-regtest-drill`;
- artifact digest: `sha256:60c7ed387a4d5d47778257806359add698100e6df52581a08fc040ea8a5b3e47`;
- merge commit: `d50e0c18b65734aa160df8b38b80f7f243160316`;
- result: **PASS_INTERNAL_ENGINEERING**.

15B qualifies the deterministic extended-regtest drill harness. It does **not**
claim public-testnet history.

## Review independence rule

15C and 15D cannot be self-certified by this repository's authoring/test process.

- 15C requires an independent protocol/state-machine reviewer.
- 15D requires an independent applied-cryptography / ZK-circuit reviewer.
- reviewer identity, scope, date, candidate commit, findings and disposition must be recorded;
- a review with no findings still requires a signed/attributed report stating the reviewed scope.

## Non-claims

Phase 15 does not claim:

- production readiness;
- mainnet readiness;
- consensus activation;
- anonymity guarantees;
- an external audit until 15C/15D reports actually exist;
- public-testnet history until operator evidence exists.

## Completion rule

`wam-privacy` becomes **handoff-complete** only after required external reviews,
extended testnet evidence, remediation closure, and maintainer package are complete.

Activation remains a separate WAM maintainer/governance decision.
