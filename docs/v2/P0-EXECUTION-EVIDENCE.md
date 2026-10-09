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
