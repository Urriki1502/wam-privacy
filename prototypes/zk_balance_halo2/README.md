# Phase 8 — Halo2 Prototype

This directory contains the isolated Halo2 experiments for WAM privacy research.

## Current implemented constraints

### Stage A — value conservation

```
spent + transparent_in
=
created + transparent_out + fee
```

### Stage B / B2 — amount domain

Every amount is range-constrained in-circuit and additionally bound to the exact WAM monetary domain:

```
0 <= amount <= 22,000,000 * 100,000,000 atoms
```

### Stage C — commitment-tree anchor

A separate `AnchorCircuit` constrains a private commitment leaf and private authentication path to a public Merkle anchor using the standard Halo2 Poseidon gadget.

The authentication-path direction is boolean-constrained at every level.

## What this establishes

The current tests demonstrate, under Halo2 `MockProver`, that:

- balanced witnesses satisfy the value relation;
- inflation and hidden-fee mismatches fail;
- amount witnesses outside the WAM monetary domain fail;
- a valid private Merkle path binds to its public root;
- wrong roots, siblings, and path directions fail.

## What this does NOT establish

The prototype does not yet prove:

- note commitment derivation from complete private note fields;
- the nullifier/spend-authority relation;
- nullifier uniqueness at consensus level;
- note encryption;
- viewing-key behavior;
- real proof generation or verification;
- production proving/verifying performance;
- WAM Core integration;
- mainnet suitability.

Phase 8 therefore remains **IN PROGRESS**.

## Dependency pins

- Rust 1.88.0
- `halo2_proofs = 0.3.5`
- `halo2_gadgets = 0.5.0`

These are research dependencies and do not imply Orchard compatibility.

## Safety boundary

Local CI only. No wallet, node, public network, mainnet/testnet funds, or production key material is used.
