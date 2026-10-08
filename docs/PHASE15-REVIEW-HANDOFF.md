# Phase 15 — External Review, Testnet and Maintainer Handoff

## Corrected internal source candidate (P0 remediation)

Current **Phase 14 internally requalified source candidate**:

`8bfbced65299a8491345b54b38bff0db498b618d`

The original internal-hardening baseline `00f8065c4f7b48fec01e4d97626ecbf2cc125852` is superseded.
Original Phase 14D/15A/15B artifacts cited below are historical and
must not be treated as qualification of the corrected source.

Phase 14D workflow:

`37623838673`

Phase 14D artifact digest:

`sha256:a41c7bb7eaa04e370acfdedc9f5c33d0b426c4c8051f6ac0efc610cfc42bdaec`

Only review documentation, qualification scripts and evidence metadata may change after the corrected source candidate. Any further protocol/circuit/wallet/verifier/Core or cryptographic source change invalidates this candidate and requires new requalification. See the updated Phase 14 status for P0 remediation runs and the changed VK identifier.

## Reviewer package

The review package binds architecture/threat-model documents, hardened circuit and serialization code, note-encryption and wallet-state code, Core-facing integration files, and Phase 1–14 qualification evidence.

## Independent state-machine review

The reviewer should attempt to falsify at least:

1. global value conservation;
2. nullifier uniqueness across accepted transitions;
3. atomic state updates;
4. rollback/replay correctness;
5. reorg restoration;
6. commitment-tree consistency;
7. shield/unshield transparent-balance binding;
8. version/network replay resistance;
9. crash/failure behavior at the Core/verifier boundary;
10. wallet recovery equivalence.

Every confirmed finding should include severity, minimal counterexample, affected invariant and a regression-test recommendation.

## Independent cryptographic / circuit review

The reviewer should examine at least:

1. Halo2 constraint completeness and unconstrained-witness risk;
2. range/cap constraints;
3. note-commitment binding;
4. nullifier construction and unlinkability assumptions;
5. authority-tag privacy assumptions;
6. domain separation;
7. key encodings and hierarchy;
8. HPKE/AEAD note-encryption usage;
9. transcript / proof-verification configuration;
10. circuit/VK identity reproducibility;
11. serialization canonicality;
12. supply-integrity failure modes.

## Extended testnet evidence

The testnet phase must record exact commits/binaries, network parameters, start/end heights and duration, shield/transfer/unshield counts, verifier accept/reject counts, duplicate-nullifier and malformed-proof rejection, wallet restart/recovery, scanner recovery, short/deep reorg drills, state/pool-balance replay equivalence, resource observations, and every incident/remediation.

A short green CI run is not extended testnet evidence.

## Handoff package

The final maintainer package must contain exact candidate commits, WAM Core dependency, protocol/circuit/version IDs, VK identity, dependency locks, deterministic build instructions, binary hashes, external review reports, remediation commits/tests, testnet history, known limitations/non-claims, and activation/rollback dependencies.

## Activation boundary

Completion of this repository does not activate anything.

Mainnet or consensus activation remains solely a WAM maintainer/governance decision.
