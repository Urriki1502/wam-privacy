# Phase 13C — Atomic Shielded State and Reorg Model

**Status:** under qualification.

Phase 13C introduces the first state-mutating shielded integration model after
the read-only Phase 13B verifier hook.

## Proof-to-state boundary

State mutation does not accept caller-declared nullifiers or output commitments.

The flow is:

```text
Phase 10D hardened envelope
        │
        ▼
real Halo2 verification
        │
        ▼
verified public metadata
(root, nullifiers, output commitments, value context)
        │
        ▼
atomic CoreShieldedState transition
```

If proof verification fails, no state metadata is produced.

## Atomic block model

A block contains one or more already verified shielded transitions.

Before publication the candidate state checks:

- exact next height;
- exact parent hash;
- every transition spends from the current anchor;
- no duplicate nullifier against prior state or within the block;
- no duplicate output commitment against prior state or within the block;
- checked shielded-pool accounting;
- exact WAM monetary cap;
- canonical Pasta-field encoding for the next anchor.

The implementation applies the block to a cloned candidate and publishes it
only after every check succeeds. Any error leaves the original state unchanged.

## Undo / reorg

Every successful block stores an undo record containing:

- previous height and tip hash;
- previous anchor;
- previous shielded pool balance;
- nullifiers added by the block;
- output commitments added by the block.

Disconnecting the exact tip restores all of those values.

Qualification includes a 300-block rollback and replacement-branch replay.

## Real-proof integration

The dedicated real-proof test:

1. builds a Phase 10D hardened circuit;
2. creates a real Halo2 proof;
3. verifies the canonical envelope;
4. extracts proof-bound root/nullifiers/output commitments;
5. applies the transition atomically;
6. disconnects the block;
7. verifies exact state restoration;
8. confirms tampered public proof metadata cannot enter the state engine.

## Deliberate boundary

Phase 13C does **not** yet derive the next commitment-tree root inside WAM Core.

The research state engine requires the higher-level commitment-tree integration
layer to supply a canonical next anchor. Production integration must derive that
root deterministically from canonical shielded outputs; it must never trust an
RPC-supplied anchor.

This phase also does not:

- accept shielded transactions into mempool or consensus;
- modify WAM Core validation;
- enable testnet/mainnet;
- provide persistent production chainstate storage.

## Exit gate

- atomic failure leaves state unchanged;
- duplicate nullifiers fail closed;
- duplicate commitments fail closed;
- stale anchor / wrong parent fail closed;
- pool underflow/overflow fails closed;
- exact tip disconnect restores prior state;
- 300-block rollback/replay passes;
- a real Phase 10D proof drives the state transition;
- tampered proof metadata cannot mutate state.

## Claim

`PHASE 13C ATOMIC SHIELDED STATE / REORG — QUALIFICATION PENDING`
