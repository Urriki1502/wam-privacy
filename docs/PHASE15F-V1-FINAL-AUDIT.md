# Phase 15F Preparation — V1 Final Internal Audit

## Purpose

This is a project-owned internal audit gate for the P0-remediated V1 release
candidate. It prepares release evidence; it cannot close external review gates.

It is deliberately stricter than "CI is green": it checks the active runtime
boundary, panic/unsafe inventory, fail-closed parser/verifier behavior, monetary
cap arithmetic, wallet atomicity, Core state rollback invariants, network gates,
and release-source immutability.

It does **not** replace the independent Phase 15C state-machine review or Phase
15D cryptographic/circuit review.

## Post-P0 merged protocol baseline

`15fafa199871f7a1688b1beda5e27005ae473d27`

Qualification/review metadata may evolve after this commit. Any change to
protocol, circuit, wallet, verifier, Core-integration or cryptographic source
invalidates this candidate and requires a new Phase 14 qualification baseline.

## Final audit surfaces

The gate inspects:

- monetary-cap constants and checked host arithmetic;
- hardened Halo2 bundle and context binding;
- canonical proof-envelope parsing;
- VK identity binding;
- HPKE note encryption and key-separation boundaries;
- shielded wallet scanning/recovery atomicity;
- Core nullifier/commitment/state/reorg logic;
- Rust FFI panic containment and regtest gate;
- generated WAM Core compile/network/resource gates;
- post-baseline source drift;
- panic-capable and unsafe primitives in active runtime files.

## Panic policy

A panic-capable primitive in an attacker-controlled or parser boundary is a
failure.

The small allowlist is limited to deterministic internal invariants that are
structurally established immediately before use. The audit report records them
explicitly rather than hiding them.

## Residual boundaries

Even with this gate green:

- Phase 15C/15D still require independent attributed review reports;
- public-testnet history is separate evidence;
- generated Core integration remains experimental/regtest-only;
- the research state model does not claim production consensus activation;
- mainnet activation remains a maintainer/governance decision.

## Logical freeze rule

V1 may reach **LOGICAL FREEZE** only after:

1. this final internal audit passes;
2. all required regression workflows on the exact head pass;
3. no known internal High/Critical finding remains open;
4. the release manifest binds the exact source/dependency/circuit/VK identity;
5. the final V1 commit is selected and no longer modified.

Only an internal logical-freeze milestone can be considered afterward.
The public v1.0.0 Git tag / GitHub Release is BLOCKED until independent
15C/15D reviews, any necessary remediation, and required operational evidence
are complete. The existence of this PR does not declare freeze or handoff complete. Until then the state
is `TAG_RELEASE_PENDING`; V2 engineering may proceed only from the immutable
frozen V1 commit on a separate versioned branch.
