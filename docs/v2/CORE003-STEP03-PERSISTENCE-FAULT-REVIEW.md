# CORE-003 Step 03 — Atomic state, reorg and persistence fault injection (R&D)

**Status:** standalone research fixture only. Not a consensus implementation, an audited storage library, a production bug fix, or proof CORE-003 is resolved.

## Baselines and scope

- Frozen V1 source: `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127`
- Frozen V2 research: `5af86cfd5be27a3275079cbccde2abd2366ebb2b`
- Step 01 PR #58: ordered Poseidon root reference, 9/9 Rust tests and 36/36 workflow runs
- Step 02 PR #59: differential V1 WalletScanner roots (0/1/2/15/16), two independently staged passes, 36/36 workflow runs at `55158e872b758febc3ca5135d2f47e13744cd386`
- Step 03 branch: `research/core003-step03-atomic-reorg-journal`, stacked on the Step 02 SHA; frozen code and actual WAM Core remain unchanged

## Threat model and invariants tested

A *single-writer, local Ubuntu filesystem* journal is modeled as a complete authenticated committed-state snapshot, not a consensus DB. The test harness uses the real frozen V1 Poseidon root primitives through the Step 01 `OrderedRootGate`.

Each snapshot stores protocol marker/version, monotonic **local** sequence, ordered per-block commitments, block height/parent/tip, per-block derived root, final derived root and a **keyed BLAKE2b MAC** over a domain-separated byte encoding. In this research fixture the MAC key is a PUBLIC fixed test value, not a secret.

1. Rebuild-from-disk rejects invalid ordering, noncanonical roots, duplicate commitments, wrong parent/height and tampered persisted state. A malformed or missing state never silently resets to genesis.
2. Writes use a temporary file with `create_new`, `write_all`, `sync_all(file)`, same-directory `rename`, and `sync_all(directory)` before reporting successful commit. No partial in-memory update is published before persistence succeeds.
3. Fault injection at **after write / before file fsync**, **after fsync / before rename**, **after rename / before directory fsync**, and **after directory fsync / before acknowledgment**. A newly recovered process must see a whole authenticated prior/new snapshot, not a partially decoded hybrid. After-rename physical-power-loss durability is *not* proven.
4. Reorg recovery checks exact tip before rollback, reconstructs Poseidon root from surviving ordered commitments, and compares replacement-chain root with fresh deterministic replay.
5. Persisted sequence advances on block append **and** rollback. Replaying an older, still-valid signed snapshot must be rejected **when an independently trusted highwater sequence is provided**; without that external witness, a valid old snapshot is intentionally accepted to demonstrate the unresolved anti-rollback boundary.
6. Duplicate acknowledgment after an injected post-rename crash must not append the same height twice.
7. No filesystem lock is implemented; **concurrent writers are outside the model**. This is explicitly a single-writer reference, not production ACID, and proves nothing about real power loss, storage controller caches, remote filesystems or malicious OS/host.

## CI method

Stage the research test source into a TEMPORARY copy of the frozen V1 Rust crate under `$RUNNER_TEMP`, use its unchanged `Cargo.lock`, Rust `1.88.0`, then execute:

`cargo test --locked --manifest-path "$RUNNER_TEMP/core003-reference/Cargo.toml" --test core003_step03 -- --test-threads=1`

Repeat in a separately staged second directory; keep Step 01 and Step 02 tests, Step 02 root vectors, the V2-05 independent clean-clone evidence and all PR-wide workflows. Require **exact-HEAD PASS** before claiming Step 03 internally qualified. A green step is not production readiness.

## Intentional blockers after Step 03

- No actual Core proof-verified transition source, canonical consensus commitment ordering, Merkle-tree specification, production depth, on-chain block anchoring or activation.
- No DB engine, authenticated key vault, tamper-resistant highwater storage, serializable multiple writers, persistent nullifier pool, verified state machine or independent fault-injection rig. The test key is a public constant.
- No verified electrical power-loss results or independent Phase15C/D cryptographic/state-machine audit.
- CORE-003 stays **BLOCKED for production**; DEV architecture review Issue #57 retains authority over consensus design. Step 04 should submit the proposed Core interface and protocol impact analysis, not modify Core without maintainer sign-off.
