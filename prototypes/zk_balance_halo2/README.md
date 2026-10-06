# Phase 8 — Halo2 Shielded Prototype

This directory contains the isolated Halo2 circuit experiments for WAM privacy research.

## Current implemented constraints

The prototype currently enforces:

```
spent + transparent_in
=
created + transparent_out + fee
```

Every monetary witness is also:

- range-constrained to 64 bits inside the circuit; and
- constrained to the exact WAM monetary domain:
  `amount <= 22,000,000 * 100,000,000 atoms`.

It uses Zcash's `halo2_proofs` crate and is currently exercised with `MockProver`.

## What this establishes

Passing tests show that the modeled balance, bit decomposition, and exact monetary-cap relations are encoded as Halo2 constraints and reject invalid witnesses.

## What this does NOT establish

The prototype does not yet prove:

- note membership;
- Merkle anchor correctness;
- nullifier derivation;
- nullifier uniqueness at consensus level;
- spend-authority binding;
- commitment correctness;
- note encryption;
- viewing-key behavior;
- real proof creation or verification;
- production performance;
- WAM Core integration.

Therefore Phase 8 remains **IN PROGRESS**, not PASS.

## Dependency baseline

The prototype targets:

- Rust 1.88.0
- `halo2_proofs = 0.4`

This tracks the current Halo2 generation used by upstream Orchard as a compatibility reference. It does not imply Orchard protocol compatibility.

## Safety boundary

Local CI only. No wallet, node, public network, mainnet, testnet funds, or production key material is used.
