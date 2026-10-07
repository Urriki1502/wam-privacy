# Phase 12B — Shielded Wallet State, Witnesses and Recovery

**Status:** under qualification.

This sub-gate turns Phase 11 note encryption into a wallet-side scanner model.

## Scanner authority

The scanner receives only an `IncomingViewingKey`.

It does not receive:

- spend authority;
- master seed;
- audit/outgoing key;
- signing material.

## State tracked

- canonical block tip;
- every shielded output commitment in canonical order;
- canonical output identifiers;
- recognized incoming notes;
- note positions;
- current authentication paths derived from the commitment tree.

## Recognition rule

A wallet credit is created only when:

1. encrypted-note encoding is valid;
2. HPKE recipient decryption succeeds under the incoming viewing key;
3. authenticated data matches network/transaction/output/context;
4. the decrypted note recomputes exactly to the public note commitment.

A ciphertext that fails wallet decryption never creates a credit.

## Reorg / recovery

Block application is atomic.

The scanner supports:

- rollback to a known canonical height;
- replacement-branch processing;
- witness recomputation after later commitments;
- deterministic full rescan from viewing capability + canonical blocks.

## Research boundary

The current tree uses the existing research `TREE_DEPTH`. Production tree capacity/encoding remains a later protocol/Core gate.

This is an executable wallet-state model, not persistent production wallet storage.
