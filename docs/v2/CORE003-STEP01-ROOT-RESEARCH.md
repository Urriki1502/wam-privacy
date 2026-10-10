# CORE-003 Research Step 01 — Canonical ordered root reference gate

**Status: adversarial research only. CORE-003 remains BLOCKED for Core/consensus production.**

## Exact lineage

- Frozen V1 implementation: `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127`
- Frozen V2 research source: `5af86cfd5be27a3275079cbccde2abd2366ebb2b`
- Separate working branch: `research/core003-canonical-root-reference`
- Actual Core reference algorithm: `prototypes/zk_balance_halo2/src/anchor.rs` and `src/wallet_state.rs` from frozen V1; no consensus changes
- Rust toolchain `1.88.0`, using the **exact frozen V1 Cargo.lock** in an ephemeral copy of the existing Rust crate; the committed V1 tree remains untouched

## Confirmed trust-boundary gap

In V1 `CoreShieldedState::apply_block_inner`, `block.next_anchor` is checked
for canonical Pasta-field encoding and assigned to `self.current_anchor`;
the commitments tracked in `HashSet` cannot by themselves reconstruct the
required append order, and the code does not derive the canonical next root
from proof-verified outputs. This is a model-level missing root binding, not
an exploit demonstrated against current WAM Core or an activated protocol.

## Local reference approach

`v2/core003_research/src/lib.rs` is an isolated, no-`unsafe`, no-RPC
reference gate staged as a temporary **integration test** in a copy of the
frozen V1 Rust crate on the CI runner. It does not change the committed V1 code. The gate:

1. Maintains an **ordered commitment vector** (unlike Core's unordered set).
2. Checks each new commitment uses a canonical `Fp` encoding and is unique.
3. Applies the **same `anchor::poseidon_pair`, `TREE_DEPTH = 4`,
   zero-padding convention, left/right pairing and append order** as
   frozen `WalletScanner::build_levels`.
4. Independently derives the expected root from the existing ordered prefix
   and proposed ordered commitments.
5. Rejects a claimed next root that is malformed OR well-formed but unequal
   to the independently computed root, without partial state mutation.
6. Models capacity limits, rejects duplicates and invalid/empty batches,
   and tests deterministic reference-only rewind/replay.

The standalone reference tests include one witness-oracle cross-check using
`anchor::merkle_root` from frozen V1. The reference model is a proof-of-concept
for the missing validation boundary, **not** a replacement for the Core model,
an external test vector or an independently validated protocol specification.

## Tests and required assertions

| Negative / regression case | Expected |
| --- | --- |
| Canonical wrong root (C != independently derived B) | `ForgedClaimedRoot` |
| Noncanonical claimed root | `NonCanonicalClaimedRoot` |
| Noncanonical commitment | `NonCanonicalCommitment` |
| Correct commitments reordered but old root reused | `ForgedClaimedRoot` |
| Duplicate against history or within batch | `DuplicateCommitment` |
| More than `2^TREE_DEPTH = 16` research leaves | `CapacityExceeded` |
| Partial-invalid batch | no mutation |
| Empty append / invalid rewind | DENY |
| Canonical rollback and replay | same deterministic root |
| One-leaf reference root | matches frozen `anchor::merkle_root` |

CI copies `prototypes/zk_balance_halo2` into `$RUNNER_TEMP/core003-reference`,
copies the research source into its `tests/core003_reference.rs`, then executes
`cargo test --locked --manifest-path "$RUNNER_TEMP/core003-reference/Cargo.toml" --test core003_reference`.
The exact V1 Cargo.lock is used, with no secondary dependency graph.
The V1/V2 regression workflows must still be green
at the exact PR HEAD. No claim of test pass before the GitHub Actions run.

## Unimplemented constraints — deliberately NOT solved in Step 01

- **No proof-origin enforcement in this reference gate:** it accepts
  caller-supplied commitments. Production must obtain them strictly from
  independently verified proof transitions and canonical block ordering.
- **No Core patch:** `CoreShieldedState` remains unchanged. This local
  reference gate does not automatically make CORE-003 PASS.
- **No production-sized tree:** research depth is still 4; final tree depth,
  append position, pruning and witness history need maintainer design.
- **No journal/database:** rollback uses a deterministic vector truncation
  fixture, not an authenticated chain-tip undo log, durable recovery, or
  transactionally committed persistence.
- **No consensus commitment:** no WAM block serialization, tree anchor
  activation, public network behavior, runtime RPC, or consensus rules.
- **No independent crypto review:** Phase15C/D reviewer work remains pending.

## Next gates (after Step 01 CI and maintainer feedback)

1. **Step 02:** freeze external reference vectors and differential tests
   against wallet-state tree (including valid proof-output ordering).
2. **Step 03:** model atomic append + authenticated reorg/restart persistence,
   with fault injection. Does not require production Core changes.
3. **Step 04:** submit proposed Core interface and protocol-impact analysis
   for explicit WAM maintainer architecture decision.
4. **Step 05 (only if authorized):** design a real Core integration on a
   fresh integration branch and qualify it from scratch; the frozen V1/V2
   sources are not retroactively modified.

**Decision needed from DEV:** confirm the intended canonical commitment-tree
hash, leaf ordering, empty-tree root, tree depth, state rollback rules and
whether a consensus change is expected. Do not merge or ship Core behavior
until this is explicitly decided.
