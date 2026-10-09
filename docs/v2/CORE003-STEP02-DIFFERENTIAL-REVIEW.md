# CORE-003 Step 02 — Differential V1 WalletScanner / OrderedRootGate Research

**Status:** proposed research CI evidence; **NOT** a Core fix, independent
cryptographic audit, trusted external known-answer vector, or consensus release.

## Pinned provenance

- Frozen V1: `95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127`
- Frozen V2: `5af86cfd5be27a3275079cbccde2abd2366ebb2b`
- Step 01 baseline / green 36 workflow runs: `1b2718a8e1ab6852949665dbb07af8ac75d2480a`, PR #58
- Step 02: `research/core003-step02-differential-roots`, separate **Draft PR**, branched from Step 01; no main or frozen source modification
- Tree oracle: frozen V1 Rust `WalletScanner::root()` and `witness_for()`, which use V1 Poseidon / `TREE_DEPTH = 4`, zero-padding and ordered append
- Local comparison: Step 01 `OrderedRootGate` staged unchanged as a sibling integration-test source in a copy of the same pinned V1 Rust crate
- Network: none; synthetic regtest-style `network_id = 3`, no real wallet, RPC, public nodes or value movements

## Deterministic input vectors

Seven new differential test cases use a **fixed wallet seed `[0x47; 32]`**
and the real V1 note encryption / serialization API. For each output index `i`
(from `0` to `16`):

- `value = 1000 + i`, `rho = Fp(10000 + i)`, `rseed = Fp(20000 + i)`;
- `transaction_digest = [1 + i; 32]`, `output_index = i`,
  `network_id = 3`, `context_digest = [0x72; 32]`;
- recipient/authority tags come from the fixed V1 key bundle;
- `note_commitment` is calculated with the actual V1 `note_identity()`;
- the ciphertext uses randomized HPKE and is not part of root vectors;
  root results are deterministic because the commitment is deterministic.

Root checkpoints from `WalletScanner` and the independent Step 01 reference
are compared for precisely **0, 1, 2, 15 and 16 commitments**. The runner
prints `CORE003_VECTOR tree N <32-byte-little-endian-field-hex>` for each
checkpoint, replays the same suite in two fresh staged copies and rejects
any difference. The five recorded lines are published as a CI artifact.

**Important limitation:** these are reproducible *internal candidate vectors*.
Their expected root hex values are generated at test time by the frozen V1
`WalletScanner`, not yet committed as reviewed known-answer constants nor
verified by an outside implementation. Keep them as research-only evidence
until an independently reviewed protocol tree specification exists.

## Security/adversarial coverage

1. Compare root after 0, 1, 2, 15 and 16 canonical note commitments.
2. Compare one-block versus partitioned multi-block append semantics.
3. Check all available owned-note Merkle witnesses and positions against
   the wallet root using the actual V1 `merkle_root` witness computation.
4. Reject reusing the root from a reordered, otherwise-valid commitment set
   without mutating the reference gate.
5. Roll back a forked block to height 0, append a different block and compare
   the resulting root and decrypted-note state with a full deterministic rescan.
6. Confirm V1 scanner rejects bad block parent, duplicate output, and >16 leaves
   without changing its committed root; reference rejects equivalent duplicate
   and capacity violations.
7. Explicitly record the **semantic mismatch for empty blocks**:
   V1 `WalletScanner` accepts a block with zero shielded outputs and maintains
   the root; Step 01 reference's `verify_and_append` rejects empty batches.
   This is *not* a failure for the current model, but must be resolved in the
   proposed Core transition API.
8. Reject malformed-field and canonical-but-forged claimed roots.

## CI requirements

The updated research-only job in `.github/workflows/v2-05-qualification.yml`
retains the frozen-path source guard, original Step 01 test run, original
V2-05 clean-clone qualification, and uses **Rust 1.88.0** + the unmodified,
locked V1 dependency graph.

1. Stage Step 01 and Step 02 files into an ephemeral copy of the V1 Rust crate.
2. Execute the existing 9 Step 01 tests and the combined Step 02 suite with
   `cargo test --locked`.
3. Stage into a second separate ephemeral copy, execute Step 02 again and
   verify the five logged checkpoint roots match byte-for-byte.
4. Upload those five root records as bounded local evidence; check that the
   checkout stays clean.
5. Require exact-HEAD required checks green before marking internal Step 02 PASS.
   Do not infer CI success from the prior commit or any previous PR.

## Open research / integration gates

- No independently specified consensus commitment-tree encoding, ordering,
  empty-tree root, depth or activation specification has been accepted by WAM.
- No production Core state interface: standalone reference receives commitments
  directly rather than extracting them from verified proof envelopes.
- No real chain-tip authorization, durable DB, journal, crash consistency or
  rollback-resistant storage.
- No public testnet / live anonymous transport evidence or external Phase15C/D
  reviewer sign-off.
- **CORE-003 remains BLOCKED** for production. No change to V1/V2 freeze, no
  merge to `main`, no WAM Core consensus patch.

## After Step 02

Review captured candidate root vectors and request maintainer confirmation
of canonical tree rules. Continue to Step 03 (atomic state/reorg persistence
fault-injection harness) on another research branch only after Step 02 exact
HEAD CI qualification.
