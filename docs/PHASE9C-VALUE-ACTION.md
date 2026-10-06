# Phase 9C — Integrated Shielded Value Action

## Purpose

Phase 9B derives the anchored input note identity directly from complete private note fields.

Phase 9C adds the missing value transition to the same proof relation.

The research action is deliberately minimal:

- one shielded input note;
- one shielded output note;
- one explicit fee.

## Private witnesses

Input note:

- value;
- recipient tag;
- spend secret;
- rho;
- rseed;
- Merkle authentication path.

Output note:

- value;
- recipient tag;
- spend-authority tag;
- rho;
- rseed.

## Public instances

1. input commitment-tree root;
2. input authority tag;
3. input nullifier;
4. output note commitment;
5. fee.

## Integrated constraints

The circuit proves all of the following together:

```
input_note = NoteCommit(
    input_value,
    input_recipient_tag,
    AuthorityTag(spend_secret),
    input_rho,
    input_rseed
)

root = MerklePoseidon(input_note, authentication_path)

nullifier = Nullifier(spend_secret, input_note)

output_note = NoteCommit(
    output_value,
    output_recipient_tag,
    output_spend_authority_tag,
    output_rho,
    output_rseed
)

input_value = output_value + fee
```

The critical composition property is that the same input and output value cells used by the value-conservation gate are also used by the corresponding in-circuit note commitments.

## Amount rules

- input shielded value is non-zero;
- output shielded value is non-zero;
- input/output/fee are 64-bit values;
- all are bounded by the exact WAM monetary cap;
- the field equation cannot be satisfied by a host-side over-cap witness.

## Negative coverage

The suite rejects:

- value imbalance;
- modified input note fields;
- modified output note fields;
- modified Merkle path;
- modified spend authority;
- zero-value shielded notes;
- one atom above the WAM cap;
- tampered public root;
- tampered authority tag;
- tampered nullifier;
- tampered output commitment;
- tampered fee.

## Real proof

The Phase 9C suite generates and verifies a real Halo2 proof for the integrated value action and verifies that each public instance is cryptographically bound.

## Boundary

This is not yet a production shielded transaction.

Phase 9C does not define:

- multi-input / multi-output bundle semantics;
- note encryption or viewing-key cryptography;
- final WAM transaction serialization;
- public value-balance encoding;
- consensus verification rules;
- mainnet activation.

Those remain explicit future gates.

## Claim

`PHASE 9C INTEGRATED VALUE ACTION — INTERNAL ENGINEERING RESEARCH`
