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
