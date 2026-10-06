# Threat Model v0.1

**Status:** Draft.

## 1. Assets

The system is intended to protect:

- spend authority;
- wallet seed material;
- receiver payment graph;
- sender/receiver address linkage;
- transaction-construction metadata;
- wallet scanning state;
- transaction-origin metadata;
- monetary-policy and supply integrity.

## 2. Adversaries

The initial model considers:

### A. Passive chain observer

Can inspect public chain history and attempt address, input, change, and timing correlation.

### B. Network observer

Can observe some wallet-to-node or node-to-peer communication and attempt origin correlation.

### C. Compromised scanner

Can read scanner-local state and scanning credentials.

Security target: this must not be sufficient to spend wallet funds.

### D. Malicious or faulty wallet component

May return malformed, stale, duplicated, or inconsistent state.

Security target: sensitive state transitions should fail closed and remain recoverable.

### E. Malicious collaborative-transaction peer

For future PayJoin work, a counterparty may provide malformed proposals, unexpected inputs/outputs, fee manipulation, or privacy-degrading constructions.

Security target: the local wallet must independently validate the complete transaction policy before signing.

### F. Implementation bug

Includes serialization disagreement, reorg handling errors, duplicate processing, stale cache state, key-derivation mistakes, and cryptographic API misuse.

## 3. Non-goals for early phases

Early WSP-1 work does not claim to provide:

- amount confidentiality;
- sender anonymity comparable to a full shielded pool;
- global network anonymity;
- protection against endpoint compromise;
- protection after spend keys are exfiltrated.

These require separate layers and separate claims.

## 4. Core invariants

The following are release-gating security properties.

### INV-01 — Spend isolation

Compromise of the scanner alone must not provide sufficient secret material to authorize a spend.

### INV-02 — Deterministic recovery

Given the same wallet secrets, chain history, and protocol version, a full rescan must reconstruct the same recognized wallet outputs.

### INV-03 — Reorg correctness

A chain reorganization must invalidate wallet observations derived solely from disconnected blocks and correctly process the replacement chain.

### INV-04 — No silent ambiguity

Malformed or insufficient chain/protocol data must not be interpreted as a successful scan result.

### INV-05 — No duplicate state transition

Reprocessing the same canonical chain event must not create a second wallet credit or an inconsistent ownership record.

### INV-06 — Signing independence

The signer must validate the spend intent and transaction data required by its policy; scanner or coordinator output is not implicitly trusted.

### INV-07 — Supply integrity

Future privacy mechanisms must preserve enforceable value conservation and must not create a path for undetectable inflation.

### INV-08 — Explicit protocol versioning

Wallet state that depends on privacy protocol behavior must record sufficient version information to prevent ambiguous reinterpretation after upgrades.

## 5. Privacy claims discipline

Every feature must state exactly what metadata it hides, from whom, and under what assumptions.

Terms such as "private", "anonymous", or "untraceable" must not be used as unqualified security claims.
