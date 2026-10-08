# Phase 15 Status

**Scope:** final project-owned review/testnet/handoff gate before any activation decision.

| Stage | Status | Evidence |
| --- | --- | --- |
| 15A — external-review / handoff package freeze | **PASS (corrected candidate; internal engineering)** | PR #48 run `37723681184`; artifact `sha256:5eb4ab6c26fd59224e496ea4473659fd81cf3ad8058780908d66c2a90d3c520a` |
| 15B — extended regtest/testnet drill harness | **PASS (corrected candidate; internal engineering)** | PR #48 run `37723681154`; artifact `sha256:edac503835d364e9585cdc7e3c0047488784e6873cce7d84e79e5a8105fe16fc` |
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

`15fafa199871f7a1688b1beda5e27005ae473d27`

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

## Merge provenance and qualification refresh (2026-10-08)

PR #47 source remediation qualified 29/29 GitHub workflows at
`74ce4f06f02c0a86cc67e2f1b393c91ab41a4888`, including Phase 15A
(run `37717858440`, artifact `sha256:460e6456fccf49b76161a39b48492fe1f9dffc64f0bbece2a8e3d5652116713c`)
and Phase 15B (run `37717858296`, artifact `sha256:ccf7a1461b4f2b240a5fd491881acbd50ab075592481add9ae68fb2bd4fe6d98`).

GitHub squash-merged PR #47 into main as
`15fafa199871f7a1688b1beda5e27005ae473d27`.
The separate PR-internal source checkpoint `8bfbced65299a8491345b54b38bff0db498b618d`
was not part of the squash-merged ancestry; it is retained only as historical
source qualification evidence. Representative critical source and lockfile blob
SHAs match between the PR head and the squash-merge commit.

This qualification-metadata update moves the baseline pin to the reachable
mainline squash commit. On this follow-up PR, repeat all required workflow
checks before merge to revalidate the integration lineage and final documentation.
No release tag or independent review claim is implied.

## V1 final internal audit and logical-freeze candidate — 2026-10-08

- PR #49 / run `37732873456`: **30/30 workflows PASS**; Phase 15F
  **internal audit** artifact
  `sha256:8b726dbba8162eeadb5855754878136bd6c157d4836349907a0990d4df4407e8`.
- Internal audit merged at
  `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127`, the chosen immutable
  **V1 logical-freeze candidate**.
- New release evidence is generated from *two separate fresh checkouts* of
  this exact source, with SHA-256 binary comparisons and the corrected VK ID;
  see `docs/PHASE15-V1-LOGICAL-FREEZE.md`.
- **Pending on this PR:** clean-checkout qualification and exact-head CI PASS.
  This section is a proposal, not a preemptive freeze PASS.
- Phase 15F **maintainer handoff** in the status table remains **PENDING**;
  Phase 15F *internal audit* PASS does not close maintainer handoff.
- Phase 15C/15D attributed external reviews, real operator testnet history,
  public release/tag and activation remain incomplete and may not be
  self-certified.
