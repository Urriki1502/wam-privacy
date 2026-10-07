# Phase 14D — Upgrade / Migration Review and Final Internal Evidence Ledger

Phase 14D is the final project-owned hardening gate before Phase 15 external
review and extended testnet work.

## Upgrade / migration contract

The current research stack has two explicitly different envelope generations:

- Phase 10C research v1: `W10C`, format version 1, circuit id `0x0A02`;
- Phase 10D hardened v2: `W10D`, format version 2, circuit id `0x0A04`.

Phase 14D requires strict rejection rather than silent migration:

- v1 bytes must not decode as v2;
- v2 bytes must not decode as v1;
- unknown/future format versions fail closed;
- unknown/future circuit identifiers fail closed;
- network/protocol changes alter the proof-context digest.

Any future real migration must therefore be explicit and version-aware.

## Static boundary inventory

The machine check inventories and hashes the production-facing research boundary:

- hardened parser/verifier;
- protocol context binding;
- C FFI;
- atomic Core-state model;
- wallet state/recovery;
- note encryption;
- generated-Core verifier wrapper.

It rejects TODO/unimplemented/debug security placeholders and requires key
fail-closed tokens such as panic containment, regtest gating, experimental Core
gating and non-blocking verifier concurrency.

Unsafe Rust tokens are permitted only in the dedicated C FFI module and are
reported in evidence.

This is not an independent manual audit.

## Final Phase 14 ledger

The final ledger binds:

- exact source head/tree;
- Cargo lock, manifest and Rust toolchain hashes;
- context/circuit/parser/FFI source hashes;
- Phase 14A release identity evidence;
- Phase 14B fuzz qualification identity;
- Phase 14C performance/resource evidence;
- Phase 14D static-review evidence.

## Completion boundary

Phase 14 may be called **internal hardening complete** only after:

- migration/version tests PASS;
- static inventory PASS;
- all repository regression workflows PASS;
- Phase 14D evidence artifact is archived.

Phase 15 remains mandatory for independent review, extended testnet history and
maintainer handoff.
