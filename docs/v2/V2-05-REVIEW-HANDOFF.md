# WAM Privacy V2-05 — Reproducible evidence and maintainer review handoff

**State:** DRAFT / RESEARCH HANDOFF. This is an evidence index and repeatable
local qualification harness, **not a product release, independent audit,
production approval, wallet activation or WAM Core consensus change.**

## Immutable starting points

| Dependency | Locked reference |
| --- | --- |
| V1 logical freeze candidate | `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127` |
| V2-04 36/36 completed GitHub workflows | `f7914ef9ee9815c573f5bf5c08dc9785deeee231` |
| V2-04 PR | [#55](https://github.com/Urriki1502/wam-privacy/pull/55) |
| V2-04 GitHub Actions example | [run 37858296962](https://github.com/Urriki1502/wam-privacy/actions/runs/37858296962) |
| WSP cryptographic signer implementation | `Urriki1502/wam-silent-payments@dcf1aecc00a64bfad3151fa202c3e07d47d83e69` |
| WAM Core historical compatibility target | `wamcoin-core-dev/wam-coin@260bc468e5adffea7ce68d8f97fac3e27e4c50b2` |
| Acceptance specification | PR #50 `docs/v2/ACCEPTANCE-TEST-MATRIX.md` (design-only, not auto-merged) |

**V2-05 exact HEAD and CI results must be read from the PR's current head**, not
pre-filled from the prior green PR. A passed check from V2-04 must not be
misrepresented as a V2-05 check.

## What is delivered

- `v2/acceptance_matrix.json`: all 29 specified CAP/FLOW/NET/CORE/PERF/COMPAT
  adversarial cases with evidence path, concrete test-symbol where available,
  evidence class and **per-case limitation**. An entry is not a production
  pass certificate.
- `v2/qualify_v2.py`: validates exact ID set, checks evidence symbols actually
  exist, rejects missing references and unsupported claims, verifies separate
  clean checkouts at exactly the same HEAD and source tree, requires frozen V1
  and V2-04 pin ancestry and hashes the evidence inputs.
- `v2/test_qualification.py`: negative tests ensuring missing cases, fabricated
  tests, evidence path errors, CORE-003 reclassification and production/audit
  claim escalation fail closed.
- `.github/workflows/v2-05-qualification.yml`: independent GitHub clean
  checkouts, V2 Python fixture replays in both, matching normalized SHA256
  evidence manifests, freeze gates and limited-scope artifact upload. Does not
  invoke public RPC, wallet addresses or live broadcast.

## How to interpret the 29-case table

The `evidence_class` field is an **evidence type**, not a permission to deploy:

- **FIXTURE_ONLY** — synthetic local unit/property tests; real runtime missing.
- **REGTEST_SIGNER** — pinned WSP PSBT and Schnorr signer checks against
  independent frozen V1 Approval/SignerGate; synthetic regtest only.
- **V1_REGRESSION_ONLY** — unchanged Rust proof/reorg/scanner/nullifier model
  tests, not a new full-stack runtime.
- **SOURCE_GUARD_ONLY** — source-drift checks, not an external compatibility
  audit or a deployed Core node.
- **PARTIAL** — modeled portions with material missing measurements or
  integrations, as specified in each limitation.
- **BLOCKED** — required condition not implemented or proven.

The authoritative result is the actual CI outcome for the exact branch HEAD.
No checkboxes are automatically upgraded from the evidence classifications.

## Unresolved blockers / residual-risk ledger

| Key | Severity | Decision required |
| --- | --- | --- |
| CORE-003 root derivation | **Production blocking** | Core maintainers must design and verify canonical shielded tree root derived from authenticated output commitments rather than caller-provided `StateBlock.next_anchor`; protocol/activation review is separate |
| Storage atomicity, snapshot anti-rollback | **Production blocking for stateful wallet operations** | Trusted monotonic checkpoint, durable atomic grant/revoke/consumption and crash/restart/reorg consistency across wallet and policy |
| User authorization | **Production blocking for transaction signing/disclosure UX** | Real trusted UI approval, cross-process isolation of issuers and keys, correct account/session display, signer authentication including hardware integration if applicable |
| Independent reviews | **Not completed** | External Phase15C state machine audit, Phase15D cryptographic audit, findings remediation and maintainer review |
| Real relay transport | **Not implemented** | Approved Tor/I2P adapter, failure-mode testing, provider independence and measured metadata leak under specified observers; no network anonymity claim |
| Performance and wallet history | **Partial** | Actual full-history wallet DB, resource budgets, fuzz/stress/DoS measurements beyond synthetic caps |
| Core/wallet integration | **Not completed** | Live node operational testnet, authenticated RPC, data model, key lifecycle, long-lived commitment tree/witness persistence and backward/forward compatibility |
| Security lifecycle | **Not completed** | Production release signing, reproducible deployment process, rollback/recovery drills, vulnerability response, governance and maintainer activation decision |

## Reproducibility

This phase's own CI checks out the V2-05 head **twice** with immutable
`github.event.pull_request.head.sha || github.sha`, fetches full history,
runs Python fixtures with `-B` (preventing bytecode output), checks worktree
cleanliness and verifies matching source tree plus per-file SHA-256 evidence.
The checked-in helper runs without sockets or a live RPC connection.

Illustrative local equivalent, after replacing `<V2-05-COMMIT-SHA>` with
the actual SHA reported by GitHub:

```bash
git clone https://github.com/Urriki1502/wam-privacy.git v2-05-a
git clone https://github.com/Urriki1502/wam-privacy.git v2-05-b
git -C v2-05-a checkout --detach <V2-05-COMMIT-SHA>
git -C v2-05-b checkout --detach <V2-05-COMMIT-SHA>
(cd v2-05-a && PYTHONPATH=v2:prototypes python3 -B -m unittest -v v2.test_policy v2.test_disclosure v2.test_routing v2.test_bridge v2.test_qualification)
(cd v2-05-b && PYTHONPATH=v2:prototypes python3 -B -m unittest -v v2.test_policy v2.test_disclosure v2.test_routing v2.test_bridge v2.test_qualification)
python3 -B v2-05-a/v2/qualify_v2.py --root v2-05-a --peer v2-05-b --output /tmp/v2-05-a.json
python3 -B v2-05-b/v2/qualify_v2.py --root v2-05-b --peer v2-05-a --output /tmp/v2-05-b.json
diff -u /tmp/v2-05-a.json /tmp/v2-05-b.json
```

**Separate CI** on the parent V2-04 and stacked V2-05 PR continues to execute
the pinned-WSP cryptographic PSBT tests, V1 Rust proof/reorg checks, and
Phase15A/F source/reviewer freeze guards. V2-05 independent checkouts use
only standard-library fixtures; they do not replace those deeper jobs.

## Maintainer handoff / requested decisions

1. Confirm whether the **wallet-local opt-in subset** (V2 policy, local
   disclosure and signer-gate composition) should be reviewed as an
   experimental optional wallet feature distinct from consensus changes.
2. Review the `SignerGate` / PSBT request-identity flow and user-consent
   boundary; identify preferred WAM wallet framework and owner for trusted
   persistence/UI integration.
3. Decide the scope of testnet/regtest operations and documentation before
   any live relay, wallet wallet-node or Core behavior is changed.
4. Separately scope the consensus-impacting shielded commitment tree,
   canonical next_anchor, verifier lifecycle and forward-compatibility review.
5. Request independent Phase15C/D crypto/state audits and agree on P0/P1
   remediation, release signing, activation and operator telemetry gates.

**No automatic merge into `main`**, no GitHub release, no on-chain activation
and no assertion that reviewers have already approved the design.
