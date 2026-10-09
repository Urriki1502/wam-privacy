# CORE-003 Step 04 — Proposed WAM Core interface and protocol-impact review

> **RESEARCH DESIGN — UNAPPROVED.** This document and its machine-readable contract are a maintainer-facing **proposal**, not an accepted consensus specification, actual Core implementation, independent audit, upgrade instruction, or authority to merge/activate anything. **CORE-003 remains BLOCKED for production.**

## Exact review scope and provenance

| Surface | Pin / actual state |
| --- | --- |
| Frozen V1 Rust proof/scanner/state model | \`95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127\` |
| Frozen V2 wallet/privacy research | \`5af86cfd5be27a3275079cbccde2abd2366ebb2b\` |
| CORE-003 Step 01 | \`1b2718a8e1ab6852949665dbb07af8ac75d2480a\` · PR #58 · research PASS |
| CORE-003 Step 02 | \`55158e872b758febc3ca5135d2f47e13744cd386\` · PR #59 · research PASS |
| CORE-003 Step 03 | \`ff604db70f5a635e406bd0a8ffd7cdfa05341a0e\` · PR #60 · 36/36 workflow runs PASS |
| Pinned WAM Core | \`wamcoin-core-dev/wam-coin@260bc468e5adffea7ce68d8f97fac3e27e4c50b2\` — research compatibility pin, NOT protocol adoption |
| V1 WSP signer | \`dcf1aecc00a64bfad3151fa202c3e07d47d83e69\` |
| Maintainer decisions | [Issue #57](https://github.com/Urriki1502/wam-privacy/issues/57) — **no independent maintainer endorsement has been recorded** |

This proposal changes **only** \`docs/v2/\`, \`v2/core003_research/\` and one project-owned CI workflow. Frozen V1, V2 and real WAM Core source must not be modified here.

## What the actual pinned code does — and does not do

- \`integration/core/phase13b/privacy_verifier.cpp\` is a **default-disabled, regtest-only, read-only proof verifier**. Generated-Core RPC \`verifyshieldedproof\` reports validity/status only. It is **not** a chainstate or mempool consensus hook.
- \`prototypes/zk_balance_halo2/src/core_state.rs\` creates \`VerifiedTransition\` through \`verify_hardened_bundle_envelope_and_decode\`, carries proof-derived nullifiers/commitments, checks tip/nullifier/pool constraints, but stores **caller-provided \`StateBlock.next_anchor\`** after canonical-field validation. A \`HashSet\` of commitments does not carry append order.
- \`prototypes/zk_balance_halo2/src/hardened_bundle.rs\` uses an experimental **fixed 2-input/2-output Halo2 proof** with nine public input fields (one input root, two nullifiers, two output commitments, fee, transparent in/out, context digest). Its current root validation is a **research** statement, not an adopted consensus encoding.
- \`prototypes/zk_balance_halo2/src/wallet_state.rs\` has a Poseidon/Pasta depth-4 (16-leaf) zero-padded commitment tree. \`WalletScanner::process_block\` accepts a block with zero shielded outputs, while \`CoreShieldedState::apply_block_inner\` rejects an empty transition vector. Empty-block semantics must be decided, not quietly assumed.
- Step 03 modeled single-writer process restarts with atomic-rename/fsync; it did **not** prove real power-loss safety, durable multiwriter chainstate, secret-key custody, protected monotonic checkpoints or real Core integration.

## Proposed trust-boundary diagram — NOT implemented

\`\`\`text
Canonical WAM block bytes from independently validated chain context
    | decode deterministic tx / shielded bundle order and context
    v
CONSENSUS-PROVIDED tx digest, fee and transparent-input/output context
    |        (never RPC declarations; transaction validity is Core-owned)
    v
Version/network/VK-gated Halo2 verifier
    |        reject bad proof; emit opaque proof-verified metadata ONLY
    v
Chainstate candidate: check parent/height/anchor policy/nullifier uniqueness
    |        append outputs in canonical tx/bundle/output order
    v
INDEPENDENTLY DERIVED Merkle root (never trust next_anchor from caller)
    |        verify monetary cap, undo record and other canonical invariants
    v
One atomic Core chainstate + shielded state/undo commit
    |        fsync/rollback/restart reconciliation under an approved DB design
    v
Accept block or reject with NO partial persistent / in-memory mutation
\`\`\`

### Candidate API and data ownership (illustrative, not ABI)

| Proposed operation | Trusted input | Output / invariant | Owner |
| --- | --- | --- | --- |
| \`parse_canonical_block(bytes, chain_context)\` | Core-validated canonical block bytes and consensus state | Deterministic transaction/bundle index and economic context | Core parser/validation |
| \`verify_hardened_envelope(context, envelope)\` | Context **derived inside Core**, pinned network, version and VK | Opaque \`VerifiedTransition\` **only after actual proof verification** | Trusted verifier boundary |
| \`stage_shielded_connect(parent_tip, verified[])\` | Canonical order + verified metadata, resolved anchor rules | Compute *candidate* nullifiers, pool, ordered append commitments and root; fail closed | Core candidate state |
| \`commit_block_atomically(candidate)\` | Every verifier/state/consensus gate complete | Commit tip, undo, nullifiers, ordered commitments, root and pool together | Core transactional storage |
| \`disconnect_exact_tip(expected_tip)\` | Verified canonical reorg and exact tip match | Apply undo transactionally, preserve deterministic replay semantics | Core reorg engine |
| \`recover_and_replay(canonical_history)\` | Committed Core chain index, authenticated state and trusted recovery policy | Reconstruct root/tip/sequence or halt safely; no silent genesis reset | Core recovery path |

**Strong requirement:** \`VerifiedTransition\` must not be constructible from arbitrary caller fields, JSON/RPC values or \`precheck\`-only results. Core must derive **transaction digest and all transparent amounts** from its own canonical validation, not a user-provided context object. Never treat a public API returning \`valid=true\` as consensus authorization.

### Candidate commitment ordering — needs explicit DEV approval

Proposed deterministic order: **block transaction index → shielded bundle index → output index 0, then 1**. Fixed \`2×2\` circuits append the two proof-verified output commitments; reject invalid canonical field encodings, duplicate commitments and over-capacity before state publication. Use only the agreed versioned hash, leaf encoding, tree depth, zero-node rules and empty-tree root. The Step 01/02 Poseidon depth-4 tree is *not* automatically the consensus standard.

**Unresolved anchor rule:** current Phase 13C checks each transition anchor equals the *current root* at block start. DEV must specify whether historical roots are permitted, the validation window, intra-block spending rules, anchor updates during a block and how reorg invalidates old anchors. Root equality alone does not answer this.

**Unresolved empty block rule:** candidate is to advance the canonical block tip without changing the shielded commitment root if a block has no shielded transitions. This is **PENDING DEV decision**; no draft code may silently reinterpret the existing \`EmptyBlock\` error.

### Proposed atomicity and recovery sequence (requires DB design)

1. Pin active tip and consensus-valid ordered block context; reject unexpected parent/network/version.
2. Verify **every** proof, transaction context and fee/UTXO accounting without publishing state.
3. Check anchor eligibility, nullifier uniqueness including in-block duplicates, canonical encoding, shielded value conservation and resource ceilings.
4. Construct candidate ordered commitment append, compute the next root **independently**, and calculate complete undo/state change.
5. Commit Core tip, nullifiers, commitment-tree nodes, undo, pool and anchor **as one transactional unit**; publish only after durability guarantees selected by DEV. Interrupted commit must recover to exactly previous or next committed state, never hybrid.
6. On reconnect/disconnect or restart, reconcile journal/database state to Core's canonical tip and reconstruct root from committed ordered history. Reject incompatible or rolled-back state under the approved threat model; do not falsely treat a local sequence counter or MAC alone as a secure anti-rollback oracle.

The Step 03 MAC uses a **public fixture key** and its file-rename model does not protect against hostile storage, concurrent Core writers, power-controller failures or valid old authenticated snapshots. Storage owner, independent highwater source and power-loss guarantees remain outside the research model.

## Consensus / compatibility impact matrix

| Proposed scope | Consensus change? | Acceptable as optional wallet-only work? | Gate |
| --- | --- | --- | --- |
| V2 policy, consent, signing approval, offline routing model | No, if **not** connected to validation | **Potentially**, after wallet architecture review | Trusted UI/signer/persistence integration |
| Read-only Phase 13B regtest proof verification | No chainstate mutation today | Experimental developer tool only | Default-off, bounded, no network activation |
| New canonical root acceptance rule or anchor window | **Yes**, if enforced in block validity | No | WAM maintainer protocol specification + governance |
| Shielded tx serialization or mempool/UTXO/value handling | **Potentially yes** | Not as wallet-only activation | Consensus/mempool compatibility analysis |
| Persistent nullifier/tree state and undo used in block acceptance | Consensus-critical state behavior | No | Atomic validation and reorg tests + Core maintainer signoff |
| New proof circuit, VK identity, network IDs, tree parameters | **Yes** if activation affects validity | No | Versioning, migration, deterministic release identity |
| Networking/privacy relay policy at wallet layer | No, if optional and local | Possibly | Transport threat model, leakage tests |
| Mainnet activation | **Yes; separate explicit approval required** | No | Full audits/testnet/operator + governance |

**Activation floor:** existing pre-activation blocks must remain unaffected; unupgraded nodes, hard-fork/soft-fork compatibility, deployment flags/heights, replay protection and invalid-chain risk need a separate explicit protocol proposal. Do not infer activation from green CI or Draft PRs.

## Adversarial invariants and acceptance requirements

Machine-readable IDs live in \`v2/core003_research/step04_contract.json\`. This design asks for negative tests covering:

- **C4-INV-01/02:** only verified proof-derived fields enter state; a canonically encoded **wrong root** and reordered output commitments are rejected atomically.
- **C4-INV-03/04:** fees, transparent balance and transaction digest must match **Core canonical truth**; no nullifier accepted twice across transaction/block/reorg replay.
- **C4-INV-05/06/07:** anchor eligibility and disconnect/restart rules; crash before/after DB transaction acknowledgement never exposes partial state; recovered tip and root agree with validated chain history.
- **C4-INV-08/09:** unsupported network/VK/circuit/format fails closed; RPC never grants consensus rights.
- **C4-INV-10/11/12:** empty blocks and 2×2 outputs follow one specified rule; rollback of an old MAC-valid snapshot is detectable only with independently trusted highwater; activation and downgrade/mixed-version behavior are defined.

**Current evidence** from Steps 01–03 supports research-level root modeling, differential vectors and local fault injection only. It does **not** close all of these Core integration gates.

## Decisions requested from WAM DEV (all OPEN)

| ID | Owner decision |
| --- | --- |
| D01 | Define versioned tree: field encoding, Poseidon parameter set, depth, domain separation, empty/zero roots |
| D02 | Canonical block/bundle/output append ordering, transaction duplicates, and blocks with no shielded output |
| D03 | Eligible spend anchors and historical-root/reorg window |
| D04 | Canonical WAM tx digest, transparent inputs/outputs, fees and UTXO verification source |
| D05 | Boundary between verifier output and Core: opaque transition API, failure codes, verifier/VK lifecycle |
| D06 | Atomic chainstate/undo/nullifier/root storage, reorg/replay and crash fault model |
| D07 | Local vs adversarial host/storage trust, key custody and independent anti-rollback highwater |
| D08 | Resource caps, verifier throughput, tree scaling and DoS / mempool admission policy |
| D09 | Whether any work becomes consensus-sensitive, activation/version rules and compatibility |
| D10 | Named independent Phase15C/15D reviewers, operator testnet criteria and release authority |

All decisions must include an explicit maintainer identity, decision date, reviewed commit, rationale, and whether a new consensus proposal is needed. **Silence is not approval.** A design reviewer may return ACCEPT DESIGN / REQUEST CHANGES / DEFER; only a separately authorized implementation and testnet/release process could later change production status.

## Future gates and nonclaims

- **Step 04** acceptance: documents, proposed interface matrix and validation script reviewed; exact-head CI green; no protected-source drift.
- **Step 05** is *not* automatically authorized: only after explicit decisions should a new regtest-only Core integration proposal even be considered.
- **Production CORE-003 remains BLOCKED**. No deployment, Core patch, wallet activation, privacy/anonymity guarantee, independent security audit, physical power-loss proof or real-funds handling is asserted.
