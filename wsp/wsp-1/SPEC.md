# WSP-1 — Static Payment Address Research Specification

**Version:** 0.1-draft  
**Status:** Research only  
**Reference:** BIP 352 Silent Payments

## 1. Purpose

WSP-1 investigates whether a BIP-352-derived static payment address scheme can be safely adapted to WAM while preserving clear scan/spend authority separation and deterministic wallet recovery.

This document is not yet a claim of wire compatibility with Bitcoin BIP 352.

## 2. Goals

WSP-1 aims to provide:

- a reusable public payment identifier;
- unique destination outputs for separate payments;
- no separate on-chain notification transaction solely for address discovery;
- deterministic receiver scanning;
- recoverability from documented wallet secret material;
- scanner operation without spending authority.

## 3. Non-goals

Version 0.1 does not provide:

- amount confidentiality;
- sender anonymity;
- a shielded pool;
- network-layer anonymity;
- consensus activation;
- custom cryptographic primitives.

## 4. Roles

### Sender

Constructs a payment to a WSP-1 address using protocol-defined transaction input data and receiver public information.

### Scanner

Processes canonical WAM chain data and identifies outputs belonging to the wallet.

### Wallet state engine

Records recognized outputs, chain position, protocol version, and rollback information.

### Signer

Holds or derives spending authority and signs only after independent wallet policy validation.

## 5. Key separation requirement

The implementation must define distinct scanning and spending capabilities.

The scanner must not require:

- wallet seed;
- base spend private key;
- derived spend private keys.

If WAM primitives make this separation impossible for a BIP-352-derived construction, the incompatibility must be documented before implementation continues.

## 6. Compatibility matrix required before coding

The first implementation PR must document WAM Core behavior for:

- elliptic-curve/key primitives;
- public-key serialization;
- supported input types;
- supported output/address types;
- transaction serialization;
- transaction identifiers;
- sighash behavior;
- wallet derivation rules;
- block/reorg APIs;
- RPC chain-consistency guarantees.

Each item must be marked:

- compatible;
- adaptable;
- incompatible;
- unknown.

Unknown items block production claims.

## 7. Scanner state

Scanner state must be reconstructible or explicitly classified as cache-only.

At minimum it should distinguish:

- chain tip identity;
- processed height/range;
- WSP protocol version;
- recognized output identifier;
- derivation metadata required by the wallet;
- rollback boundary.

## 8. Required failure behavior

The scanner must fail closed on:

- malformed key material;
- unsupported transaction form;
- missing protocol-required transaction data;
- inconsistent chain cursor;
- impossible derivation state;
- unsupported WSP version.

A failure must not be silently converted into "no payment found".

## 9. Reorg behavior

On a reorganization:

1. detect divergence from the stored canonical chain identity;
2. invalidate scanner state derived from disconnected blocks;
3. roll back wallet observations tied only to those blocks;
4. scan the replacement canonical branch;
5. preserve idempotence when blocks are replayed.

## 10. Required test classes

Before WSP-1 can advance beyond prototype:

- deterministic positive vectors;
- deterministic negative vectors;
- malformed transaction vectors;
- duplicate block/transaction replay;
- restart at arbitrary scan boundaries;
- full rescan equivalence;
- short and deep synthetic reorgs;
- multiple payments to one static address;
- multiple wallets scanned against the same chain fixture;
- scanner-state corruption;
- unsupported-version handling.

## 11. Security invariants

WSP-1 inherits repository invariants and adds:

### WSP-INV-01

A successful scan must be reproducible from the same canonical chain and wallet scan material.

### WSP-INV-02

Scanner-only secret material must be insufficient to authorize a spend.

### WSP-INV-03

An unsupported or ambiguous transaction form must not generate a recognized wallet credit.

### WSP-INV-04

Replay of already processed canonical data must not duplicate wallet ownership state.

## 12. Next specification step

Version 0.2 should be written only after the WAM compatibility matrix is completed against a locked WAM Core commit.
