# Phase 10A — Shielded Bundle Semantics

**Status:** qualification candidate.

Phase 10A promotes the already-general Phase 7 transition model into an explicit bundle contract before any multi-action Halo2 circuit is attempted.

## Bundle scope

The executable model supports up to:

- 256 shielded spends;
- 256 shielded outputs;
- transparent input;
- transparent output;
- one explicit fee.

This phase validates the semantics required for multiple actions. It does not define a production transaction encoding.

## Conservation

For every accepted bundle:

```
sum(spent shielded notes)
+ transparent_in
=
sum(created shielded notes)
+ transparent_out
+ fee
```

The modeled shielded pool must track the same relation:

```
new_pool
=
old_pool
+ transparent_in
- transparent_out
- fee
```

The fee term is mandatory. Omitting it leaves phantom value in pool accounting even when the transition-level conservation equation is correct.

## Additional fail-closed invariant

```
sum(spent shielded notes) <= old_pool
```

This prevents malformed model state from spending commitments whose disclosed fixture values exceed the pool value represented by the state.

## Qualification cases

Phase 10A covers:

- two-input / two-output private bundle;
- mixed shielded + transparent flow;
- fee removal from pool balance;
- duplicate input/nullifier inside one bundle;
- commitment/output uniqueness inherited from Phase 7;
- aggregate WAM monetary-cap enforcement;
- malformed state where spends exceed pool accounting;
- 256-action shape limit.

## Boundary

Phase 10A is an executable semantic contract only.

It does not yet provide:

- one ZK proof for multiple actions;
- variable-length consensus serialization;
- note encryption;
- viewing-key cryptography;
- production nullifier/commitment encodings;
- WAM Core verification or activation.
