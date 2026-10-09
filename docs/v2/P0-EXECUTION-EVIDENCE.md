# P0 execution evidence and acceptance contract

Research coordinator: E (internal separate sub-agent, not external audit).
V1 immutable source: 95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127.
V2 immutable source: 5af86cfd5be27a3275079cbccde2abd2366ebb2b.
Main observed HEAD: db3d2dcaa540f1129d540101813b761167d33174.

## Verified starting evidence

CORE-003 research PRs #58–61 are Draft and unmerged. GitHub Actions listing
at each exact head returned 36 completed-success workflows:
#58 1b2718a8e1ab6852949665dbb07af8ac75d2480a,
#59 55158e872b758febc3ca5135d2f47e13744cd386,
#60 ff604db70f5a635e406bd0a8ffd7cdfa05341a0e,
#61 847b59f00550b516a35e821253ba8f99a5aca575.
This proves research checks only. CORE-003 production remains BLOCKED.

Coordinator observed V2 freeze 44 success check-runs (including repeated
V2-05 runs). Main and V1 freeze directly returned zero check-runs; no direct
exact-SHA green claim is made for those commits. V2 recursive tree was complete
and contained no AGENTS.md.

## Scope and honest result classes

E's baseline harness executes existing V2 policy/disclosure/routing/bridge/
qualification and V1 signer tests, forbids changes to protected baseline source,
checks actual checkout against event head, and emits a bounded artifact.
BASELINE_REGRESSION_ONLY is not acceptance of new persistence implementations.
CI success must be read from GitHub at the current PR head, not this manifest.

A: authenticated snapshot and durable policy research.
B: persistent signer reservation journal research.
C: recovery contract/fault tests, then actual A/B integration.
D: trusted UI boundary, FFI and disclosure internal adversarial review.
E: separately read A/B/C/D source and execute cross-module regression before
reporting integrated PASS. Two checkouts are reproducibility, not an external
cryptographic/security audit.

## Mandatory handoff evidence

Every PR reports current full head SHA, test commands and count, exact-head run/
job URLs, failures and limitations. Subsequent commits invalidate earlier-head
acceptance. Required cases: authenticated old snapshot denied after revocation/
consumption, independent trusted checkpoint unavailable fails closed, consent
replay denied across restart, durable signer pre-reservation precedes side effect,
crash windows do not repeat provider action, request identity/fingerprint conflict
denied, concurrent threads/processes serialize, corrupt/truncated journal fails
closed, cross-module crash never combines an old grant with a fresh signer state.
A/B integration requires concrete adapters and real executable tests; interface
document consistency alone is DESIGN_CONTRACT_ONLY.

Freeze refs, main and WAM Core/consensus remain untouched. All tests are offline
fixtures; no public node, real wallet, real keys, funds or deployment.
Production anti-rollback depends on independently trusted monotonic storage and
reviewed key management. File fsync and process fault tests do not prove physical
power-loss durability. Production readiness and external audits remain pending.

## Independent lane reproduction and historical guard conflict

E workflow separately checks out pinned lane source, verifies frozen paths,
executes each lane suite and stores source SHA + test output artifacts:
A b8a5d84e3c981ce1d97b52d6c0af4aa23422d7be (12 durability tests);
B fc90ff5962d4c354f28e631d56f79c5efd09fa44 (11 journal + 19 original signer);
C d00ed6ad793b56a53dd68d200910436e666081fd (8 contract + 12 actual A/B composition);
D f8c8623bfda2789507dccbc0ea18fcff49c3076a (8 adapter + 28 policy + 23 disclosure).
E stages only pinned A/B research adapter directories for the C matrix job.
C now executes actual conservative sequential A/B composition; distributed ACID
and complete SEC-003 acceptance remain BLOCKED.
B review prompted corrupt DB and shared process provider-count tests; those
tests and identity/capabilities binding fixes were independently read at B pin.

Observed historical inherited Phase15F run 37915791762 associated with E
246246371bd2bda6faf83c695b3dde85019f4925 failed V1-FREEZE-001, rejecting added
.github/workflows/v2-p0-regression-research.yml. Job 113771515226 actually
checked out synthetic merge 8feaf327824561ab4b6c3e7780edd077dc6282f8.
Historical audit/review package permits explicit v2-01 through v2-05 workflow
filenames; the broad v2-* naming allowed elsewhere does not satisfy that gate.
The protected sources are unchanged; full inherited CI is not green.
Historical guards are preserved. A reviewed research scope decision is needed
before full inherited qualification can accept additive research workflows.

All targeted and reproduction CI results remain subject to current-head
GitHub verification. Pending/queued is never PASS. Runtime physical durability,
trusted monotonic deployment, real consent UI, atomic recovery integration,
CORE-003 approval and external audits remain blockers.

## Final source review and observed targeted evidence

E independently read stable C d00ed6ad's coordinator and 12 actual composition
tests. The coordinator copies capability input, binds exact scope and approval,
checks authenticated A grant fields/consumption/revocation/expiry/clock and B
durable fingerprint/result, and permanently blocks uncertain intents. Tests
kill processes at seven commit/provider cuts, reopen real databases, count
provider calls across processes, reject cache after revoke/expiry, missing or
mixed participant receipts, changed approvals and caller mapping mutation.
Runtime at this stable C SHA remains PENDING until CI observation.

E independently fetched targeted job logs:
A b8a5d84: run37915843539/job113771687177, 100 tests OK;
B fc90ff59: run37915908355/job113771902602, 30 tests OK;
D f8c8623: run37915830167/job113771642086, 59 tests OK.
These establish targeted research suites only, not full inherited green CI.
Original E baseline old SHA246246371bd2bda6faf83c695b3dde85019f4925:
run37915792083/job113771517303, 113 tests OK. This does not qualify later E
workflow changes; final E exact-head A/B/C/D reproduction remains PENDING.

All five current lane comparisons to V2 freeze contain only new scoped files,
no overlapping changed paths and no pre-existing source edits. Internal
cross-agent review/reproduction remains distinct from external security audit.
