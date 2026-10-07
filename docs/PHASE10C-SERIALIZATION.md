# Phase 10C — Canonical Research Serialization and Verifier Contract

**Status:** under qualification.

Phase 10C defines a strict research envelope for the fixed 2×2 Phase 10B Halo2 proof.

It is not a WAM consensus transaction encoding.

## Envelope v1

Canonical byte order:

1. 4-byte magic: `W10C`;
2. little-endian format version `1`;
3. little-endian circuit id `0x0A02` for the fixed 2×2 research circuit;
4. 32-byte verifier-key identifier supplied by the integration profile;
5. one-byte public-instance count, fixed at `8`;
6. eight canonical Pasta `Fp` representations in Phase 10B public-instance order;
7. little-endian `u32` proof length;
8. proof bytes.

No trailing bytes are allowed.

## Public-instance order

The eight field elements are:

1. shared input root;
2. input 0 authority tag;
3. input 0 nullifier;
4. input 1 authority tag;
5. input 1 nullifier;
6. output 0 note commitment;
7. output 1 note commitment;
8. fee.

## Fail-closed parser rules

The decoder rejects:

- wrong magic;
- unknown format version;
- unknown circuit id;
- wrong public-instance count;
- non-canonical field encodings;
- truncated encodings;
- empty proofs;
- proofs larger than the research cap;
- trailing bytes.

The verifier additionally rejects a verifier-key identifier that does not match the caller's expected deployment profile.

## Verification contract

The decoded public instances are passed, unchanged and in canonical order, to Halo2 `verify_proof`.

A qualification test generates a real Phase 10B proof, serializes it, parses it, and verifies it through this contract. Tampering either a public instance or proof byte is rejected.

## Deliberate non-claims

Phase 10C does not yet bind:

- WAM network identity;
- a transaction digest;
- transparent input/output value balance;
- a production verifying-key digest derivation;
- note encryption or viewing keys;
- production commitment-tree parameters;
- WAM Core consensus parsing.

Those are later gates. This envelope is versioned so those changes do not need to be silently reinterpreted.
