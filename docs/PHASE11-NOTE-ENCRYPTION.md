# Phase 11 — Shielded Key Hierarchy and Note Encryption

**Status:** under qualification.

Phase 11 adds an explicit separation between spend authority and note-viewing capabilities, then encrypts note plaintext with an established standard rather than a WAM-specific cryptographic construction.

## Cryptographic profile

Research ciphersuite:

- RFC 9180 HPKE;
- DHKEM(X25519, HKDF-SHA256);
- HKDF-SHA256;
- ChaCha20-Poly1305;
- pinned Rust `hpke` dependency.

This is not wire-compatible with Zcash Orchard. Orchard is used as a design reference for spend/view separation and in-band note-secret delivery; WAM's research transport uses HPKE so the composition itself is standardized.

## Key separation

A master seed deterministically derives three disjoint capabilities:

```
master seed
├── spend-authority material
├── incoming viewing material
└── audit/outgoing viewing material
```

The incoming viewing type contains no spend-authority material. A scanner can therefore receive only the incoming viewing key.

The public shielded address contains:

- incoming HPKE public key;
- audit/outgoing HPKE public key;
- recipient tag;
- spend-authority tag.

The spend-authority tag is committed inside the Phase 10D note relation and is no longer exposed as a public proof instance.

## Note plaintext

The canonical v1 plaintext carries:

- value;
- recipient tag;
- spend-authority tag;
- rho;
- rseed;
- bounded memo.

Values are non-zero and capped at the exact WAM monetary maximum. Field encodings are canonical and unknown versions/trailing bytes fail closed.

## Associated data

HPKE authenticated data binds ciphertext to:

- network id;
- transaction digest;
- output index;
- note commitment;
- Phase 10D context digest.

Moving a ciphertext to another transaction/output/context causes decryption failure.

## Selective disclosure

Each note is encrypted twice with independent HPKE encapsulations:

- recipient copy → incoming viewing key;
- audit/outgoing copy → audit viewing key.

Neither viewing capability includes spend-authority material.

## Exit gate

- deterministic seed recovery recreates the same public address;
- incoming/audit keys are distinct;
- both authorized viewing roles decrypt;
- wrong keys and cross-role ciphertexts fail;
- AAD tampering fails;
- encryption is randomized;
- plaintext/ciphertext parsers reject malformed inputs;
- amount, memo and address-binding rules fail closed;
- prior Phase 1–10D regressions remain green.

## Non-claims

This phase does not define mainnet addresses, final wallet storage, hardware-key custody, WAM Core consensus serialization or production activation.
