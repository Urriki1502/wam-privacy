# Phase 9A — Integrated Anchored-Spend Action

## Purpose

Phase 9A closes the explicit composition gap left by Phase 8C and Phase 8D.

Earlier stages proved two relations separately:

- commitment-tree membership;
- spend-authority / nullifier derivation.

Phase 9A assigns one private `note_identity` cell and constrains that same cell into both relations inside one Halo2 circuit.

## Integrated relation

Private witnesses:

- `spend_secret`;
- `note_identity`;
- Merkle authentication siblings;
- Merkle direction bits.

Public instances:

1. commitment-tree root;
2. authority tag;
3. nullifier.

The circuit constrains:

```
root = MerklePoseidon(note_identity, path)

authority_tag = Poseidon(AUTHORITY_DOMAIN, spend_secret)

note_key = Poseidon(spend_secret, note_identity)
nullifier = Poseidon(NULLIFIER_DOMAIN, note_key)
```

The critical composition property is that `note_identity` is assigned once and the exact same constrained cell is used as both:

- the commitment-tree leaf;
- the note input to nullifier derivation.

## Negative tests

The original public relation is rejected when any of the following changes:

- private note identity;
- private spend authority;
- Merkle sibling;
- Merkle direction;
- public instance ordering.

## Real proof

The Phase 9A suite creates and verifies a real Halo2 proof for the integrated action.

The produced proof is rejected when any public output is modified:

- root;
- authority tag;
- nullifier.

## Remaining boundary

Phase 9A still treats `note_identity` as a circuit-native field element.

It does not yet derive that identity from complete private note fields such as:

- value;
- recipient/viewing tag;
- spend authority tag;
- rho;
- randomness.

That note-field-to-commitment relation is the next composition layer.

## Claim

`PHASE 9A INTERNAL COMPOSITION PASS`

This is an isolated research result, not a production note format, audit, consensus rule, anonymity guarantee, or mainnet proposal.
