# Phase 13B — Generated WAM Core Regtest Verifier Hook

**Status:** under qualification.

Phase 13B connects the qualified Phase 13A Rust/C verifier ABI to a generated WAM Core tree without modifying WAM Core consensus validation or persistent state.

## Integration shape

\`\`\`text
generated WAM Core
       │
       │ experimental / regtest-only RPC
       ▼
privacy_verifier.cpp
       │
       │ stable C ABI
       ▼
Phase 13A Halo2 verifier
\`\`\`

The hook is deliberately read-only.

It does not accept or connect a shielded transaction, modify chainstate, insert nullifiers, update anchors, or alter mempool/consensus rules.

## Default-off build contract

The generated tree always contains the small wrapper source, but the RPC and Rust ABI dependency are enabled only when the build supplies:

\`\`\`
WAM_PRIVACY_CPPFLAGS=-DENABLE_WAM_PRIVACY_EXPERIMENTAL
WAM_PRIVACY_LIB=<qualified verifier library>
\`\`\`

Without the compile flag, the RPC is not registered and the wrapper returns \`NOT_COMPILED\` without referencing Rust verifier symbols.

## Runtime boundary

Even an experimental build rejects every network except regtest.

The RPC validates:

- envelope hex shape and maximum size;
- exact 32-byte transaction digest;
- non-negative host amounts;
- Phase 13A monetary-cap checks;
- protocol/network/transaction context binding;
- transparent value balance;
- verifying-key identity;
- Halo2 proof validity.

The returned result is only:

- \`valid\`;
- stable verifier \`status\`.

No secret data is returned.

## Generated-tree patch safety

The patcher validates every anchor before writing any generated-Core file.

If any expected WAM Core anchor moves, the patch aborts without leaving a partially patched generated tree.

The patch is idempotent and qualification checks require exactly one marker for each integration point.

## Qualification gate

Phase 13B requires:

- patcher unit tests;
- idempotent application;
- fail-without-partial-write behavior;
- wrapper compilation with the feature disabled;
- wrapper compilation with the feature enabled;
- exact WAM Core revision pin;
- generated WAM Core source patch verification;
- experimental \`wamd\` build linked to the Phase 13A verifier library;
- regtest RPC registration;
- malformed-proof rejection;
- chain height unchanged across verifier RPC calls;
- non-regtest invocation rejection.

## Boundary

Phase 13B remains an integration/research hook.

Phase 13C is the first stage allowed to model atomic shielded state transitions and reorg rollback. That work must remain isolated and disabled by default.
