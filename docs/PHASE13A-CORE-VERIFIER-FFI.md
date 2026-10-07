# Phase 13A — Core Verifier FFI Boundary

**Status:** under qualification.

Phase 13A is the first Core-facing shielded-verifier integration gate.

WAM Core is C++, while the qualified Phase 10D Halo2 verifier is Rust. This phase therefore defines a narrow, stable C ABI before any WAM Core source change is proposed.

## ABI model

The library exports an opaque verifier handle:

```text
Core process
   │
   ├─ verifier_new()
   │      ↓
   │   Params(k=15)
   │   pinned Phase 10D verification key
   │
   ├─ verifier_vk_id()
   │
   └─ verify_hardened_v1(
          canonical envelope,
          network,
          tx digest,
          transparent in,
          transparent out,
          fee
      )
```

The verifier handle owns parameters and the verification key so they are not regenerated for every proof.

## Fail-closed boundary

Phase 13A rejects:

- null pointers;
- malformed lengths;
- non-regtest network ids;
- transparent amounts above the WAM monetary cap;
- malformed/canonical-envelope failures;
- verifying-key id mismatch;
- protocol/network/transaction context mismatch;
- transparent balance mismatch;
- invalid Halo2 proofs.

Rust panics are contained with `catch_unwind` and converted to a fixed ABI error code. No panic may unwind across the C boundary.

## Network gate

Only `NetworkId::Regtest` is accepted.

Mainnet and testnet are deliberately disabled at this stage.

## ABI artifacts

- Rust module: `src/ffi.rs`;
- C header: `include/wam_privacy_halo2.h`;
- shared/static library build via Cargo crate types;
- exported-symbol CI check.

## Qualification gate

Phase 13A requires:

- Rust format/clippy PASS;
- C header compilation PASS;
- real Phase 10D proof verification through the C-facing ABI;
- deterministic VK identity match across direct Rust and ABI paths;
- wrong-network replay rejection;
- wrong transaction-context rejection;
- malformed-envelope rejection;
- over-cap host input rejection;
- shared/static library build;
- expected exported ABI symbols present.

## Boundary

This phase does not modify WAM Core consensus code.

Phase 13B may begin only after 13A passes, and must remain regtest-only / disabled by default.
