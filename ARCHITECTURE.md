# WAM Privacy Architecture v0.1

**Status:** Draft / research architecture.

This document defines the initial component boundaries for privacy work in WAM. It deliberately avoids assuming that every Bitcoin, Monero, or Zcash primitive can be transplanted into WAM unchanged.

## 1. Architectural objective

The target system should improve privacy across four distinct surfaces:

1. **address privacy** — reduce reusable on-chain identifiers;
2. **transaction privacy** — reduce common transaction heuristics;
3. **wallet privacy** — minimize metadata and isolate sensitive authority;
4. **network privacy** — reduce transaction-origin correlation.

A future fifth surface, **shielded state**, is research-only and must not be coupled to early phases.

## 2. Layer model

```text
┌───────────────────────────────────────┐
│ Layer 6 — Shielded research           │
│ proofs / notes / nullifiers / audit   │
├───────────────────────────────────────┤
│ Layer 5 — Collaborative privacy       │
│ PayJoin / coordinated construction    │
├───────────────────────────────────────┤
│ Layer 4 — Network privacy             │
│ broadcast / RPC / transport isolation │
├───────────────────────────────────────┤
│ Layer 3 — Wallet privacy              │
│ coin selection / metadata policy      │
├───────────────────────────────────────┤
│ Layer 2 — Signer abstraction          │
│ software / offline / hardware future  │
├───────────────────────────────────────┤
│ Layer 1 — WSP-1                       │
│ static address / receiver scanning    │
├───────────────────────────────────────┤
│ Layer 0 — Security foundation         │
│ recovery / reorg / state integrity    │
└───────────────────────────────────────┘
```

Layers may depend downward, not upward.

## 3. Primary trust boundary

The first strong boundary is between **scanning** and **spending**.

```text
WAM chain data
     │
     ▼
┌──────────────┐
│ WSP Scanner  │
│ scan ability │
└──────┬───────┘
       │ detected wallet events
       ▼
┌──────────────┐
│ Wallet State │
└──────┬───────┘
       │ spend request
       ▼
┌──────────────┐
│    Signer    │
│ spend secret │
└──────────────┘
```

### Scanner may possess

- material strictly required to recognize incoming payments;
- public spend information required by the selected protocol;
- chain cursor and deterministic derived scan state.

### Scanner must not possess

- wallet seed;
- base spend private key;
- derived spend private keys;
- release, treasury, or maintainer credentials.

A scanner compromise may reduce privacy. It must not grant spending authority.

## 4. Signer abstraction

Future wallet code should target a narrow signer interface rather than a concrete key store.

Conceptually:

```text
Wallet Engine
     │
     ▼
SigningProvider
 ├─ SoftwareSigner
 ├─ OfflineSigner
 └─ HardwareSigner   (future)
```

Hardware integration is not a prerequisite for WSP-1 research.

## 5. Chain-integration rule

Before any BIP-352-derived implementation is called WAM-compatible, the implementation phase must verify WAM Core assumptions including:

- supported key and curve primitives;
- transaction input and output types;
- sighash and transaction serialization behavior;
- wallet key derivation;
- reorg semantics;
- script / address rules;
- node RPC guarantees.

Compatibility must be demonstrated, not assumed.

## 6. Shielded research isolation

Shielded-pool work must remain isolated from production wallet code until all of the following exist:

- a protocol specification;
- explicit value-conservation rules;
- nullifier and commitment invariants;
- deterministic test vectors;
- negative/adversarial vectors;
- independent review;
- dedicated testnet or regtest validation;
- supply-integrity analysis.

No custom proof system should be invented for WAM merely to accelerate delivery.

## 7. Cross-repository relationship

`wam-privacy` defines privacy protocols, prototypes, and privacy-specific invariants.

`wam-security` may independently validate reusable security properties such as crash consistency, recovery, fuzz behavior, fail-closed RPC handling, and patch regressions.

Neither repository should silently redefine WAM consensus.
