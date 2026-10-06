# Phase 1 Evidence Ledger

This file records immutable evidence identifiers for Phase 1 qualification work.

## Gate A — WSP contract / self-test

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

Status: **PENDING**

Required next evidence:

- exact daemon built from target Core commit;
- daemon SHA-256;
- local/private regtest qualification report;
- two-node E2E;
- reorg depths;
- recovery and final accounting.

Use `scripts/run_phase1_local.sh` on trusted local/self-hosted hardware.
