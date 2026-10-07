# Phase 14A — Reproducible Dependency and Release Identity

Phase 14A establishes the minimum reproducibility boundary required before security review.

## Inputs that must be pinned

- repository commit;
- Rust toolchain;
- Cargo dependency graph;
- hardened circuit identifier;
- protocol version;
- deterministic Halo2 verifying-key identifier.

## Release identity

A qualification manifest must bind at least:

```text
source commit
rustc version
Cargo.toml SHA-256
Cargo.lock SHA-256
rust-toolchain.toml SHA-256
protocol version
circuit id
verifying-key id
static library SHA-256
shared library SHA-256
```

The manifest is engineering evidence, not a signing/attestation format.

## Reproducibility gate

The qualification runner will:

1. consume the committed lockfile with `cargo --locked`;
2. build release artifacts twice into clean target directories;
3. compare the resulting static/shared verifier library SHA-256 values;
4. derive the VK identifier independently on each build path;
5. fail closed on any mismatch;
6. publish the evidence manifest as a CI artifact.

## Boundary

Phase 14A does not yet claim:

- cross-OS bit reproducibility;
- deterministic proof bytes;
- supply-chain provenance beyond the pinned dependency graph;
- external reproducible-build verification;
- production artifact signing.

Those remain later release/audit concerns.
