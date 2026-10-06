# Phase 8 — Isolated ZK Prototype

## Stage A — Balance circuit

Phase 8 begins with the smallest consensus-critical arithmetic statement from the Phase 7 model:

```
spent + transparent_in
=
created + transparent_out + fee
```

This statement is now represented as an actual Halo2 constraint prototype.

### Why start here

Supply integrity is the first non-negotiable shielded invariant. A protocol that hides values but permits an unconstrained value path is unacceptable.

### Current limitations

The Stage A circuit uses field elements derived from `u64` host values, but **does not yet range-constrain those values inside the circuit**.

That means Stage A is useful for API/proof-system integration and constraint-shape validation, but it is not yet a sound monetary circuit.

Before Stage A can graduate:

1. each amount must be range-constrained;
2. overflow/wraparound cases must be negative-tested;
3. public/private exposure must be specified;
4. actual proof creation and verification must be added;
5. deterministic proof/verification fixtures should be recorded where appropriate.

## Planned Phase 8 stages

### Stage B — Range-constrained value balance

Add bit/range constraints for all amount witnesses.

### Stage C — Commitment-tree anchor

Bind a spent note witness to a commitment-tree anchor derived from Phase 7 semantics.

### Stage D — Nullifier relation

Prove the modeled spend-authority/nullifier relation without exposing the secret authority.

### Stage E — Proof generation / verification

Move beyond `MockProver` to real Halo2 proof creation and verification in isolated CI.

### Stage F — Differential bridge

Cross-check accepted/rejected transitions between:

- Phase 7 Python state model;
- Phase 8 Halo2 circuit fixtures.

## Status

`PHASE 8-A — IN PROGRESS`

No production, anonymity, or mainnet claim is implied.
