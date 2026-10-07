# Privacy Roadmap

This roadmap is intentionally gate-based. A later phase is not considered started merely because experimental code exists.

## Phase 0 — Architecture freeze

Deliverables:

- architecture v0.1;
- threat model v0.1;
- security/research boundary;
- design principles;
- WSP-1 specification skeleton;
- upstream reference set;
- inventory of reusable WAM privacy assets.

Exit gate:

- trust boundaries are explicit;
- security invariants are named;
- assumptions requiring WAM Core verification are listed;
- existing WSP-1 work is identified as a baseline rather than duplicated.

## Phase 1 — WSP-1 adoption and requalification

Goal: adopt the existing `wam-silent-payments` WSP-1 qualification build and determine whether it remains compatible with current WAM Core.

Existing baseline already includes:

- BIP-352 derivation and official vectors;
- durable scanning and atomic block state;
- deterministic recovery and rollback;
- deep reorg testing;
- PSBTv2 construction/signing;
- differential testing;
- coverage-guided fuzzing;
- local two-node E2E;
- fail-closed scanner behavior.

Required work now:

- pin current WAM Core revision;
- compare current Core against the previously qualified Core revision;
- complete the WAM compatibility matrix;
- rerun contract, unit, adversarial, reorg, recovery and integration suites;
- rerun relevant differential and fuzz gates when protocol-sensitive code changes;
- record any new WAM-specific deviations;
- keep mainnet/testnet namespace and profile decisions explicitly unresolved until maintainers adopt them.

Exit gate:

- current WAM Core revision is pinned;
- no relevant unreviewed Core delta remains;
- zero known false negatives in normative vectors;
- expected negatives do not produce wallet credits;
- full rescan is deterministic;
- scanner-only compromise does not grant spend authority;
- reorg and restart suites pass;
- qualification evidence is reproducible;
- external/adoption blockers remain explicitly marked rather than treated as engineering PASS.

## Phase 2 — Privacy-aware wallet

Research:

- coin-selection metadata;
- change policy;
- address/account metadata isolation;
- wallet logging policy;
- privacy diagnostics without false guarantees.

Exit gate:

- wallet policy is deterministic where required;
- privacy-sensitive logs are minimized;
- regression suite covers policy changes.

## Phase 3 — Signer abstraction

Implement a narrow `SigningProvider` boundary.

Targets:

- software signer;
- offline signer fixture;
- hardware-signer interface placeholder.

Exit gate:

- wallet engine contains no hidden dependency on one concrete key store;
- signer validates required transaction policy independently.

## Phase 4 — PayJoin

Research both:

- BIP-78 deployed PayJoin;
- BIP-77 asynchronous PayJoin.

Exit gate:

- malicious proposal tests;
- fee/output/input policy validation;
- signing only after complete local validation;
- no custodial coordinator requirement in the design.

## Phase 5 — Network privacy

Research:

- wallet RPC isolation;
- transaction broadcast strategy;
- peer and timing metadata;
- optional privacy transports.

Exit gate:

- explicit network observer model;
- measurable metadata reduction;
- no claim of anonymity from transport changes alone.

## Phase 6 — Collaborative privacy extensions

Only after PayJoin behavior is stable.

Any CoinJoin-style research must remain non-custodial and must define coordinator trust assumptions.

## Phase 7 — Shielded protocol research

Study mature systems, especially Zcash Orchard/Halo 2.

Research topics:

- note model;
- commitment tree;
- nullifiers;
- viewing capabilities;
- value balance;
- proof verification;
- upgrade/versioning model;
- supply integrity.

Exit gate:

- written protocol/state semantics — **PASS (internal engineering)**;
- formal value-conservation statement — **PASS**;
- deterministic vectors — **PASS**;
- negative vectors — **PASS**;
- independent expert review plan — **PASS (plan defined; external review pending)**.

Current status: **INTERNAL ENGINEERING PASS**. This does not authorize Phase 8 production claims or mainnet work.

## Phase 8 — Isolated ZK prototype

Allowed only after Phase 7 gate.

Environment:

- local/regtest/testnet only;
- no production wallet claims;
- no mainnet activation proposal until independent review and extended validation exist.


## Phase 9 — Integrated shielded action research

Status through 9C: **INTERNAL ENGINEERING PASS**.

Completed gates:

- 9A — one in-circuit note identity shared by Merkle membership and nullifier derivation;
- 9B — complete private note fields derive the anchored/nullified note commitment;
- 9C — one shielded input → one shielded output + explicit fee with in-circuit value conservation.

This remains research-only and does not define production bundle serialization or consensus verification.

## Phase 10 — Bundle semantics and multi-action composition

### Phase 10A — Executable bundle semantics

Goals:

- validate multiple shielded inputs and outputs;
- enforce aggregate nullifier uniqueness;
- enforce aggregate commitment uniqueness;
- account transparent input/output and fee exactly;
- preserve global WAM monetary-cap accounting.

Exit gate:

- two-input/two-output positive bundle passes;
- duplicate input/nullifier fails closed;
- mixed transparent/shielded flow conserves exactly;
- fee cannot leave phantom pool value;
- malformed pool accounting fails closed;
- Phase 7/8 semantic bridge remains reproducible.

### Phase 10B — Multi-action Halo2 relation

Allowed only after 10A PASS.

Target: a fixed-shape research circuit first, before any variable-length/bundle encoding claim.

### Phase 10C — Serialization and verifier contract

Allowed only after 10B PASS.

Define canonical research serialization, public-instance ordering, verifier input contract, versioning, and malformed-encoding rejection. No WAM Core activation is implied.

Exit gate:

- deterministic canonical encoding;
- strict version/circuit identifier handling;
- canonical field parsing;
- no trailing or ambiguous bytes;
- explicit verifying-key identifier contract;
- real Phase 10B proof verifies after encode/decode;
- malformed/tampered public inputs and proof bytes fail closed.

### Phase 10D — Protocol hardening and context binding

Required before any protocol freeze.

Goals:

- define domain separation for note, nullifier, Merkle-node and future encryption contexts;
- replace research-only tree depth with an explicit capacity/performance decision;
- define production-valid spend/view key encodings rather than unconstrained field-element placeholders;
- bind proof verification to protocol/network/transaction context;
- define transparent value-balance binding for shield/unshield flows;
- freeze circuit/version identifiers and a reproducible verifying-key identity;
- use checked/fail-closed arithmetic at host/parser boundaries.

Exit gate:

- context replay across incompatible versions/networks is rejected;
- tree/key/domain parameters are explicit and versioned;
- transparent/shielded value balance cannot diverge between outer transaction and proof;
- circuit/verifying-key identity is reproducible.

## Phase 11 — Shielded key hierarchy and note encryption

Goals:

- explicit spend authority, incoming viewing capability and optional outgoing/audit capability;
- note plaintext format;
- reviewed AEAD/KDF construction using established primitives;
- trial-decryption / note-discovery behavior;
- selective disclosure without spend authority;
- deterministic recovery vectors and negative vectors.

Exit gate:

- viewing capability cannot authorize spends;
- malformed ciphertext fails closed;
- note discovery/recovery is deterministic;
- encryption test vectors are versioned;
- no custom cryptography is introduced without independent review.

## Phase 12 — Real wallet, signer and network adapters

Promote the Phase 2–6 policy models into actual WAM integrations.

Required work:

- WSP wallet integration;
- real WAM transaction / PSBT adapter;
- real cryptographic signer provider and offline/hardware-compatible boundary;
- BIP-78 and/or BIP-77 PayJoin transport profile chosen explicitly;
- Tor/I2P/OHTTP runtime adapters where adopted;
- shielded note scanning, witness maintenance, recovery and reorg handling;
- end-to-end telemetry redaction.

Exit gate:

- local/regtest end-to-end wallet flow uses real WAM transaction structures;
- signer policy is enforced against real serialized transactions;
- network fallbacks remain fail-closed;
- restart/recovery/reorg tests pass.

## Phase 13 — WAM Core isolated shielded verifier integration

Environment: regtest/testnet only, disabled by default.

Goals:

- strict Core parser for the versioned proof envelope;
- proof verification against the pinned circuit/verifying-key profile;
- atomic anchor/nullifier/state updates;
- duplicate-nullifier rejection at state level;
- reorg rollback/replay;
- shield/unshield supply accounting;
- resource/DoS limits for verification.

Exit gate:

- malformed proof/encoding cannot crash or partially mutate state;
- disconnect/reconnect and deep reorg restore identical canonical state;
- supply accounting remains conserved;
- feature remains non-mainnet and explicitly gated.

## Phase 14 — Hardening and release qualification

Required before external production review:

- dependency lockfiles and reproducible builds;
- deterministic protocol/test vectors;
- parser/verifier fuzzing;
- differential implementations where practical;
- circuit constraint inventory;
- proving/verifying performance and memory benchmarks;
- adversarial resource-limit tests;
- upgrade/version migration tests;
- static/security review of wallet/Core integration;
- release artifact hashes and evidence ledger.

Exit gate:

- no known high/critical internal finding remains open;
- reproducible qualification report binds source, dependencies, circuit/VK identity and binaries;
- test vectors and fuzz corpora are archived.

## Phase 15 — Independent review, extended testnet and maintainer handoff

This is the final project-owned gate before any activation decision.

Required:

- independent state-machine review;
- independent cryptographic/circuit review;
- remediation and regression tests for every confirmed high/critical finding;
- extended isolated/public testnet history;
- wallet recovery/reorg/upgrade drills;
- final protocol specification and non-claims;
- maintainer review package with exact commits, build instructions, hashes and activation dependencies.

Completion boundary:

`wam-privacy` may be called **handoff-complete** after Phase 15 evidence is complete.

Mainnet/consensus activation remains a separate WAM maintainer/governance decision and is never implied by this repository alone.
