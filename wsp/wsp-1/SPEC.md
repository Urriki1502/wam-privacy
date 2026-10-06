# WSP-1 — Static Payment Address Profile

**Version:** 0.1-draft  
**Status:** Research / adoption review  
**Reference:** BIP 352 Silent Payments  
**Existing implementation baseline:** `Urriki1502/wam-silent-payments@feat/wsp1-v1.0`

## 1. Purpose

WSP-1 defines the WAM profile for a BIP-352-derived static payment address scheme while preserving clear scan/spend authority separation and deterministic wallet recovery.

A substantial qualification implementation already exists. This repository therefore treats WSP-1 as an **adopt-and-requalify** effort, not a greenfield rewrite.

This document is not yet a claim of mainnet WAM adoption or universal wire compatibility.

## 2. Existing engineering baseline

The existing WSP implementation reports:

- BIP-352 v1.1.1 derivation;
- official vector coverage;
- scan secret separated from base spend secret;
- durable SQLite scanning state;
- atomic per-block commits;
- deterministic rollback and recovery;
- real two-node reorg testing;
- PSBTv2 offline signing;
- local integration with WAM Core v0.1.11 on regtest;
- differential and fuzz qualification evidence.

These results are reusable evidence, but they must be rebound to a current WAM Core revision before new compatibility claims are made.

## 3. Goals

WSP-1 aims to provide:

- a reusable public payment identifier;
- unique destination outputs for separate payments;
- no separate on-chain notification transaction solely for address discovery;
- deterministic receiver scanning;
- recoverability from documented wallet secret material;
- scanner operation without spending authority.

## 4. Non-goals

WSP-1 does not provide:

- amount confidentiality;
- sender anonymity;
- a shielded pool;
- network-layer anonymity;
- automatic mainnet activation;
- custom cryptographic primitives.

## 5. Roles

### Sender

Constructs a payment to a WSP-1 address using protocol-defined transaction input data and receiver public information.

### Scanner

Processes canonical WAM chain data and identifies outputs belonging to the wallet.

### Wallet state engine

Records recognized outputs, chain position, protocol version, and rollback information.

### Signer

Holds or derives spending authority and signs only after independent wallet policy validation.

## 6. Key separation requirement

The implementation must define distinct scanning and spending capabilities.

The scanner must not require:

- wallet seed;
- base spend private key;
- derived spend private keys.

The existing qualification build follows this model; requalification must verify that no new integration path violates it.

## 7. Compatibility matrix

WAM Core behavior must be pinned and reviewed for:

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

Each item is classified:

- compatible;
- adaptable;
- incompatible;
- unknown.

Unknown items block production claims.

## 8. Scanner state

Scanner state must be reconstructible or explicitly classified as cache-only.

At minimum it should distinguish:

- chain tip identity;
- processed height/range;
- WSP protocol version;
- recognized output identifier;
- derivation metadata required by the wallet;
- rollback boundary.

## 9. Required failure behavior

The scanner must fail closed on:

- malformed key material;
- unsupported transaction form;
- missing protocol-required transaction data;
- inconsistent chain cursor;
- impossible derivation state;
- unsupported WSP version.

A failure must not be silently converted into "no payment found".

## 10. Reorg behavior

On a reorganization:

1. detect divergence from the stored canonical chain identity;
2. invalidate scanner state derived from disconnected blocks;
3. roll back wallet observations tied only to those blocks;
4. scan the replacement canonical branch;
5. preserve idempotence when blocks are replayed.

## 11. Required qualification classes

Before current-Core qualification can pass:

- deterministic positive vectors;
- deterministic negative vectors;
- malformed transaction vectors;
- duplicate block/transaction replay;
- restart at arbitrary scan boundaries;
- full rescan equivalence;
- short and deep synthetic/isolated reorgs;
- multiple payments to one static address;
- multiple wallets scanned against the same chain fixture;
- scanner-state corruption;
- unsupported-version handling;
- current WAM Core integration.

## 12. Security invariants

WSP-1 inherits repository invariants and adds:

### WSP-INV-01

A successful scan must be reproducible from the same canonical chain and wallet scan material.

### WSP-INV-02

Scanner-only secret material must be insufficient to authorize a spend.

### WSP-INV-03

An unsupported or ambiguous transaction form must not generate a recognized wallet credit.

### WSP-INV-04

Replay of already processed canonical data must not duplicate wallet ownership state.

## 13. Current qualification target

Current WAM Core head observed during Phase 0:

`wamcoin-core-dev/wam-coin@260bc468e5adffea7ce68d8f97fac3e27e4c50b2`

Previously qualified WSP Core baseline:

`wamcoin-core-dev/wam-coin@8a3f4fe4f1d804c378f795d4cc281ec5125f75f3`

The current head is 41 commits ahead of that baseline. The observed delta does not modify the Core wallet/transaction/consensus source areas used by WSP; it is still subject to qualification reruns before compatibility is promoted.

## 14. Next specification step

Version 0.2 should incorporate the completed current-Core compatibility matrix and recorded qualification evidence.
