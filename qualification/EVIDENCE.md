# Phase 1 Evidence Ledger

This file records immutable evidence identifiers for Phase 1 qualification work.

## Gate A — original WSP contract / self-test baseline

- GitHub Actions run: `37458973866`
- source head: `3b834454b240268e4387a3e5a52a9e0e8ee1f9f1`
- WSP pin: `a8522fee9b6eda285998a5ff4a45d6bc4eb991b3`
- result: **PASS**
- artifact: `phase1-wsp-contract`
- artifact digest: `sha256:c568f136369431348ef13adc78a91f30100f9ceeeacfdd07fbb986f073b5a307`

Completed steps:

- checkout pinned WSP source;
- Python 3.12 setup;
- pinned dependency installation;
- formatting check;
- lint;
- internal self-test;
- black-box WSP contract conformance.

## Gate A2 — macOS PTY portability fix

Observed on the macOS current-Core run:

- WSP self-test: **150/150 PASS** before the fix;
- black-box contract: **PASS**;
- independent differential: **10,000/10,000 PASS**;
- WSP-E2E-001: **PASS**;
- WSP-E2E-002: **PASS**;
- WSP-E2E-003: failed when the offline signer's `getpass()` escaped to the caller's controlling terminal.

Fix:

- WSP PR #8 — macOS offline-signer PTY isolation;
- merged WSP commit: `dcf1aecc00a64bfad3151fa202c3e07d47d83e69`;
- workflow run `37463840923`: **PASS**;
- workflow run `37463840992`: **PASS**;
- post-fix self-test: **151/151 PASS**.

The fix changes only the local qualification harness process/session boundary. It does not change WSP cryptography, transaction semantics, wallet policy, or WAM consensus.

## Gate B — WAM Core guarded-source drift

- GitHub Actions run: `37458974176`
- source head: `3b834454b240268e4387a3e5a52a9e0e8ee1f9f1`
- previously qualified Core: `8a3f4fe4f1d804c378f795d4cc281ec5125f75f3`
- current Core target: `260bc468e5adffea7ce68d8f97fac3e27e4c50b2`
- result: **PASS**
- artifact: `phase1-core-drift`
- artifact digest: `sha256:d64d417885971363cc6a938b588c0ef0eebb5e000eb4ea71a98e7b9a8817c34b`

Meaning of PASS:

No changed path entered the automated guarded Core source/build surfaces.

This does **not** establish runtime or consensus compatibility.

## Gate C — current-Core isolated regtest

Status: **PASS (internal engineering)**

Pinned runtime:

- WSP commit: `dcf1aecc00a64bfad3151fa202c3e07d47d83e69`;
- WAM Core commit: `260bc468e5adffea7ce68d8f97fac3e27e4c50b2`;
- macOS arm64 `wamd` SHA-256: `99a5f20fb741620de3655fcab980b3303d8caa2bbb6025dc490eb8cca4074a34`.

Observed final Gate C evidence:

- self-test: exit code 0;
- black-box contract: exit code 0;
- independent differential: 10,000/10,000 PASS, exit code 0;
- real-node suite: WSP-E2E-001 through WSP-E2E-007 all PASS;
- real reorg depths: 1 / 12 / 100 / 300 all PASS;
- interop suite: SP2-001 through SP2-010 all PASS;
- regtest suite: SPREG-001 through SPREG-009 all PASS;
- final evidence result: `PASS`;
- runner terminator: `PHASE1_MACOS_GATE_C_PASS`;
- local evidence path: `reports/phase1-macos/gate-c-evidence.json`.

Atheris/libFuzzer is intentionally excluded from the macOS Gate C run; Linux fuzz evidence remains tracked separately.

### Phase 1 closure

All internal engineering gates required by the Phase 1 roadmap are now satisfied against the pinned current Core revision.

Remaining blockers are external by design:

- independent security/cryptographic review;
- maintainer adoption of production network profile/namespace;
- any future mainnet or consensus activation decision.
