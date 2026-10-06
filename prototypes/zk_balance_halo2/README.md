# Phase 8-A — Halo2 Balance Prototype

This directory contains the first isolated zero-knowledge circuit experiment for WAM privacy research.

## Scope

The circuit enforces exactly one relation:

```
spent + transparent_in
=
created + transparent_out + fee
```

It uses Zcash's `halo2_proofs` crate and is exercised with `MockProver`.

## What this establishes

A passing test shows that the modeled arithmetic relation is encoded as a Halo2 constraint and that invalid witnesses fail the mock constraint system.

## What this does NOT establish

This prototype does not yet prove:

- note membership;
- Merkle anchor correctness;
- nullifier derivation;
- nullifier uniqueness at consensus level;
- spend-authority binding;
- amount range constraints;
- commitment correctness;
- note encryption;
- viewing-key behavior;
- real proof creation or verification;
- production performance;
- WAM Core integration.

Therefore Phase 8 remains **IN PROGRESS**, not PASS.

## Dependency pin

The prototype targets:

- Rust 1.88.0
- `halo2_proofs = 0.3.5`

The dependency choice follows current Zcash Orchard usage as a compatibility reference, not as a claim of Orchard compatibility.

## Safety boundary

Local CI only. No wallet, node, public network, mainnet, testnet funds, or production key material is used.
