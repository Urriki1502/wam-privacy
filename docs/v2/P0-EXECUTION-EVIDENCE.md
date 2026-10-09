# P0 research evidence and CI stabilization

Implementation owner: root Codex. Independent reviewer: E, read-only.
The implementation team is now one author and one reviewer. Agents A-D no longer write branches.

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
Research push branches are appended; normalized branch concurrency cancels duplicate push/PR workflow runs.
Historical guard scripts and every runtime/test-source blob are unchanged.
The staged trees were reviewed before branch updates. Root owns the common CI file sequentially across research branches; independent agents do not edit it.

## Current reproducible matrix

| Lane | Draft PR | Current reviewed source |
| --- | --- | --- |
| A | #70 | 5da526b380d1788875d1133c0a6623b2fcdda09e |
| B | #67 | fe41f504d8f4064fd0bc5f01adc1c13733c22fa9 |
| C | #71 | d4e33ae114fcc1c32c95766b5dfe7f429b599cc3 |
| D | #69 | 2ace9ccae6f727d0498cbfbeca20be817e1e8058 |

E reproduces these current immutable source SHAs, checks protected baseline files, runs the original historical freeze audit and review-package generation, and executes each isolated suite.
C's private runtime dependencies intentionally remain A b8a5d84e3c981ce1d97b52d6c0af4aa23422d7be and B fc90ff5962d4c354f28e631d56f79c5efd09fa44.
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
Internal source review and separate-agent reproduction do not substitute for external audit. No production or mainnet readiness claim is made.
