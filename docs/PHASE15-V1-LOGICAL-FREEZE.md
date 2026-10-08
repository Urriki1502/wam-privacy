# WAM Privacy V1 — Logical Freeze Candidate / Internal Release Evidence

**Candidate source SHA:** `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127`

**Status:** **PENDING clean-checkout qualification on this PR.** Once the
`V1 - Logical freeze clean-clone qualification` workflow and all required
existing GitHub checks complete successfully and this PR is merged, the exact
candidate source commit may be treated as the **V1 INTERNAL LOGICAL FREEZE**.
This is **not** a GitHub tag, GitHub Release, independently audited release,
public-testnet qualification or mainnet activation.

## Provenance and why we pin this exact commit

- Post-P0 Halo2 fixed-domain / proof-origin transition fix merged at
  `15fafa199871f7a1688b1beda5e27005ae473d27` (PR #47).
- Phase 15A/15B baseline corrected in
  `d3d6fb4ae877de02b2b99749c673a698dbf98b19` (PR #48).
- V1 final **internal** audit merged in
  `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127` (PR #49).
- No later changes to `prototypes/zk_balance_halo2/`, `integration/core/`,
  or V1 runtime/state tests are permitted without explicitly invalidating the
  logical freeze and choosing a freshly qualified new candidate.

## V1 protocol/runtime identity

| Field | Pinned value |
| --- | --- |
| WAM supply cap | 22,000,000 WAM (2,200,000,000,000,000 atomic units) |
| Protocol version | `1` |
| Hardened research circuit ID | `2564` (`0x0A04`) |
| Halo2 verifier K | `15` |
| Expected corrected VK ID | `1e7850f15106f20f35dbfb282b696703d0263264ba10a4eaef71601fa46312da` |
| Rust toolchain | `1.88.0` |
| WAM Core Phase 1 qualification pin | `wamcoin-core-dev/wam-coin@260bc468e5adffea7ce68d8f97fac3e27e4c50b2` |
| WSP qualification pin | `Urriki1502/wam-silent-payments@dcf1aecc00a64bfad3151fa202c3e07d47d83e69` |

These are pinned **research and prior qualification inputs**. The WAM Core
commit is not a claim that upstream HEAD is still unchanged or approved.

### Why the old V1 evidence is not interchangeable

The pre-P0 VK ID
`de8ae5b7a5a149c11587f6b0e14f61954aea404461642a6ad1eb18b3a5b1700a`
and earlier Phase 14D baseline `00f8065...` are superseded for this candidate.
The repository's earlier committed `qualification/phase14a-release-identity.json`
is **historical**, not the release identity of this frozen source. The fresh
workflow derives VK ID and binary digests from the pinned source and compares
them with the corrected expected profile.

## Reproducibility process

The new workflow:

1. Checks out the qualification PR with full Git history and, separately,
   checks out the **exact pinned V1 SHA** twice into two clean directories.
2. Verifies both clean repositories have the expected HEAD and tree, and that
   the PR has not modified protected V1 implementation/test paths.
3. Uses Rust `1.88.0`, a locked Cargo dependency graph and isolated build
   output directories to compile the release verifier independently twice.
4. Checks deterministic protocol/circuit/VK identity in both checkouts.
5. Requires bit-identical SHA-256 hashes for both static and shared verifier
   libraries, re-runs the fixed-domain regression and records all hashes.
6. Creates an immutable `git archive` of the pinned source, a JSON evidence
   manifest, a manifest checksum and experimental verifier binaries as one
   GitHub Actions artifact.

**Evidence is scoped to two clean source checkouts on the same hosted runner.**
It does not prove cross-platform reproducibility, an independent audit or
production readiness.

## Manual reproduction (research only)

```bash
git clone https://github.com/Urriki1502/wam-privacy.git
cd wam-privacy
git checkout --detach 95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127
cd prototypes/zk_balance_halo2
cargo build --release --locked
cargo run --release --locked --quiet --example release_identity
cargo test --locked --test security_domain_binding
```

The GitHub Actions artifact `v1-internal-logical-freeze-evidence` (after
a successful run) contains the full SHA-256 release manifest, exact build hashes,
source archive and research binaries. Do not copy older binary digests into a
new manifest without actually rebuilding.

## Known limitations and mandatory blockers

- Independent Phase 15C state-machine and 15D cryptographic/circuit reviews:
  **PENDING** (external, attributed reports).
- Phase 15E remediation closure: **PENDING EXTERNAL FINDINGS**.
- Extended *operator-run* testnet history and maintainer adoption: **PENDING**.
- `CoreShieldedState` still accepts `StateBlock.next_anchor` from the
  experimental higher-level integration; production canonical tree-root
  derivation and verified transition/state connection are not complete.
- Merkle tree research depth and Core generated hook remain limited;
  generated Core integration is regtest-only and disabled by default.
- Actual V1 `v1.0.0` tag / GitHub Release: **TAG_RELEASE_PENDING**; not
  authorized merely by passing internal engineering checks.
- Consensus/network activation remains an external WAM maintainer/governance
  decision. This project may not self-authorize mainnet activation.

## V2 separation after the logical freeze

Any V2 implementation must begin on a distinct versioned branch rooted from
the immutable V1 commit above. V1 source must not be rewritten/rebased.
Cross-cutting fixes to V1 require explicit de-freeze and new qualification.
The V2 design-only PR #50 is not an exception to the V1 source freeze;
V2 check/workflow policy must be separated without turning off V1 safety gates.

## Final release/handoff checklist (not yet closed)

- [ ] Clean-source qualification workflow PASS on exact PR head.
- [ ] All mandatory V1 CI gates PASS on exact PR head.
- [ ] Qualification metadata merged without V1 runtime drift.
- [ ] V1 internal logical freeze recorded with exact candidate SHA.
- [ ] Independent Phase 15C/15D review reports and actionable findings resolved.
- [ ] Extended real testnet evidence and final maintainer review.
- [ ] Final authorized Git tag / GitHub Release (if approved).
