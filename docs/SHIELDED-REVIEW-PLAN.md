# Phase 7 — Independent Review Plan

Phase 7 is an executable protocol-state model, not a production cryptographic design. Independent review should therefore occur in two stages.

## Stage A — State-machine review

Reviewer profile:

- cryptocurrency protocol engineer;
- consensus/state-machine experience;
- familiarity with UTXO privacy systems or shielded pools.

Review questions:

1. Can any accepted transition violate value conservation?
2. Can one note produce more than one valid spend path?
3. Can a nullifier be replayed across transitions?
4. Can a note that is absent from the commitment state be spent?
5. Can commitment ordering or duplicate commitments create ambiguous roots?
6. Can viewing capability accidentally imply spend authority?
7. Can unknown versions be interpreted permissively?
8. Is pool accounting consistent with shield/unshield flow?

Required output:

- written findings;
- severity;
- minimal counterexample or invariant reference;
- proposed test vector for every confirmed issue.

## Stage B — Cryptographic design review

This stage begins only after a future Phase 8 proof-system design exists.

Reviewer profile:

- applied cryptographer;
- zero-knowledge proof-system implementation experience;
- familiarity with Halo 2 / Orchard or comparable systems.

Review questions will include:

- commitment binding/hiding assumptions;
- nullifier unlinkability and uniqueness;
- note encryption and viewing-key separation;
- circuit soundness;
- range constraints;
- value-balance constraints;
- anchor/witness validation;
- domain separation;
- serialization;
- proof verification failure behavior;
- parameter / upgrade governance;
- supply-integrity failure modes.

## Required evidence before any mainnet proposal

A future production proposal must not rely only on this repository's internal CI. At minimum it should include:

- frozen protocol specification;
- deterministic and negative test vectors;
- differential implementation where practical;
- circuit constraint inventory;
- fuzzing of parsers / verification boundaries;
- reproducible builds;
- isolated testnet history including reorg/recovery tests;
- independent cryptographic review;
- remediation record for all high/critical findings;
- maintainer approval.

## Current status

Stage A is **READY FOR EXTERNAL REVIEW** after Phase 7 merges.

Stage B is **NOT STARTED** because no production ZK construction exists.
