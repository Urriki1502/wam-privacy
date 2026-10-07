# Phase 10B — Fixed 2×2 Halo2 Bundle

**Status:** qualification candidate.

Phase 10B lifts the Phase 10A bundle semantics into one fixed-shape Halo2 relation.

## Shape

- 2 shielded inputs;
- 2 shielded outputs;
- 1 explicit public fee;
- both input notes anchored to one public commitment-tree root.

Variable-length bundles are deliberately out of scope.

## Public instances

1. shared input root;
2. input 0 authority tag;
3. input 0 nullifier;
4. input 1 authority tag;
5. input 1 nullifier;
6. output 0 note commitment;
7. output 1 note commitment;
8. fee.

## In-circuit invariants

The circuit proves:

- each input note is derived from its private value, recipient, authority, rho and rseed;
- each input authentication path resolves to the same public root;
- each nullifier is derived from the same note identity used by its Merkle path;
- the two nullifiers are distinct using a non-zero inverse constraint;
- each output commitment is derived from complete private output fields;
- the two output commitments are distinct using a non-zero inverse constraint;
- all four shielded note values are non-zero;
- each amount and the fee are 64-bit and no greater than the WAM monetary cap;
- aggregate input and aggregate output-plus-fee are independently capped;
- aggregate input equals aggregate output plus fee.

## Fixed-shape reason

A 2×2 circuit provides a deterministic proving shape for qualification. It avoids prematurely defining variable-length consensus encoding, padding rules, or recursive aggregation.

## Boundary

This is still research-only. It does not define:

- production note encryption;
- viewing-key cryptography;
- canonical transaction bytes;
- variable-length bundle semantics;
- WAM Core verifier integration;
- consensus or mainnet activation.
