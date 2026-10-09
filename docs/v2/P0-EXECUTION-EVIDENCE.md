# P0 research evidence and CI stabilization

Implementation owner: designated project maintainer. Review scope: separate internal read-only evidence check; no independent human audit claimed.
Research branches are updated sequentially by the project maintainer; reproducibility is independently checked by isolated CI executions.

Frozen V1 source: 95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127.
Frozen V2 source: 5af86cfd5be27a3275079cbccde2abd2366ebb2b.
Main observed HEAD: db3d2dcaa540f1129d540101813b761167d33174.
Freeze refs, main, WAM Core/consensus and protected runtime sources remain unchanged.
All execution uses offline fixtures; no public node, real wallet or funds.

## Failure diagnosis and concrete repair

Failed A/B/D jobs were read individually. All observed failures rejected the standalone research workflow filename through V1-FREEZE-001 or PHASE15A_BASELINE_INVALIDATED.
Example B: run37915908352/job113771903031 rejected .github/workflows/v2-sec002-research.yml.
C/E final pre-repair jobs were queued; their runtime behavior had not been verified.
These observations do not establish that all unexecuted tests pass.

Root moved each isolated research job into .github/workflows/v2-05-qualification.yml, which the existing audit and review-package guards already allow, and deleted the standalone workflow.
Original V2-05 qualification jobs, PR paths and dispatch event are preserved.
P0 E uses pull_request checks on its research branch; duplicate push events were removed, while default V2-05 push, PR and manual triggers remain enabled.
Historical guard scripts and every runtime/test-source blob are unchanged.
Each staged tree is checked for change scope before branch update. The shared CI workflow is updated sequentially to avoid conflicting edits.

## Current reproducible matrix

| Lane | Draft PR | Current reviewed source |
| --- | --- | --- |
| A | #70 | 4f2a81acb66bfe35ae2ea0ec878e21f608f76130 |
| B | #67 | 059658db638229abac23f077e9318466bf501a63 |
| C | #71 | 618c69d63ef1b0447474ac61a826e40bcd0f6857 |
| D | #69 | 2e127bb068be90890e396b8dfc2a5b7d3120322b |

E reproduces these current immutable source SHAs, checks protected baseline files, runs the original historical freeze audit and review-package generation, and executes each isolated suite.
C's private runtime dependencies now use verified research heads A 4f2a81acb66bfe35ae2ea0ec878e21f608f76130 and B 059658db638229abac23f077e9318466bf501a63.
Their adapter source blobs match the new CI-only heads. E overlays only those pinned research directories for C, never frozen source.
The baseline runner qualifies existing baseline tests only. Current C includes 12 actual A/B composition tests and 8 contract tests; process crash, restart, concurrency and mixed receipt cases must execute successfully before runtime acceptance.

## Historical verified evidence

Earlier targeted suites were independently verified from exact-source job logs:
- A b8a5d84e: run37915843539/job113771687177, 100 tests OK.
- B fc90ff59: run37915908355/job113771902602, 30 tests OK.
- D f8c8623b: run37915830167/job113771642086, 59 tests OK.
- E old baseline 246246371bd2bda6faf83c695b3dde85019f4925: run37915792083/job113771517303, 113 tests OK.

These results do not qualify the newer CI heads above. New runs and artifacts must be observed at the current SHA. QUEUED, cancelled duplicates and source review are never PASS.
CORE-003 research #58-61 each previously had 36 completed-success workflows at their recorded heads; production remains BLOCKED pending maintainer approval.
V2 freeze had 44 success check-runs including repeats; main and V1 freeze directly returned zero check-runs, so no direct exact-SHA green claim was made for them.

## Acceptance and remaining limits

Require successful current-head historical guards, targeted restart/rollback/concurrency tests, preserved baseline regression, exact checkout evidence, and reviewed failures.
A/B/C storage is trusted and outside the rollback attacker domain. SQLite does not supply a hardware monotonic checkpoint or detect jointly rolling back all trusted stores.
C permanently blocks interrupted non-COMPLETE intents and never refunds consumed authority or retries an uncertain provider. This sacrifices liveness and does not implement distributed ACID.
Real trusted UI deployment, C++ FFI lifetime integration, independent external state-machine/crypto reviews and CORE-003 approval remain open.
Internal source review and separately pinned CI reproduction do not substitute for external audit. No production or mainnet readiness claim is made.

## Latest pinned-lane refresh — October 9, 2026

The currently pinned research lanes in this CI attempt are A `4f2a81acb66bfe35ae2ea0ec878e21f608f76130` (PR #70), B `059658db638229abac23f077e9318466bf501a63` (PR #67), C `618c69d63ef1b0447474ac61a826e40bcd0f6857` (PR #71) and D `2e127bb068be90890e396b8dfc2a5b7d3120322b` (PR #69), with A/B previously verified and C/D advanced by documentation-only cleanup commits. These new C/D SHA pins and this refreshed E head require new exact-HEAD CI evidence before qualification can be claimed. C overlays exactly the updated pinned A/B research adapters in its isolated fixture tests. The historical earlier SHAs and their logs remain historical evidence, not qualification of the current refresh.

This PR modifies only the already allowed V2-05 workflow and this E evidence document; the original baseline runner, CI qualification jobs, frozen V1/V2 implementation, Core and consensus are unchanged. P0 E's redundant push event is removed to prevent cancelled push/PR duplicates. This commit requires a new exact-head CI success; previous E green results are insufficient for the refreshed lane matrix.

All lanes use offline synthetic tests. Production integration, trusted monotonic storage, distributed atomicity, independent security audit, FFI/UI integration and CORE-003 remain BLOCKED or pending maintainer approval.

## Documentation provenance cleanup

The research source code and test runners are unchanged by the C/D document-only revisions. Internal analysis is not independent external security review; maintainers should rely on exact-source tests, named reviewer signoff and clearly bounded claims, not on historical contributor workflow labels. Git history and earlier evidence remain intact. Full P0 E qualification requires all checks at this new source/merge context to pass.
