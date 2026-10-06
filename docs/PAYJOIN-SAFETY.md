# Phase 4 — PayJoin Safety Layer v0.1

**Status:** sender-side safety prototype  
**Wire protocol:** not implemented  
**Transport:** not implemented  
**Consensus impact:** none

BIP 78 is deployed and defines the original synchronous PayJoin protocol. BIP 77 defines Async PayJoin and is currently a Draft BIP.

WAM Phase 4 starts with the **sender proposal-validation boundary**, not networking.

## Why validator-first

The highest-value failure mode is not "the HTTP request failed".

It is:

> a malicious or buggy counterparty returns a proposal that the sender signs even though it changes the sender's economic intent.

Therefore transport is downstream of proposal safety.

## PJ-INV-01 — original sender inputs remain

Every sender input from the original transaction must remain in the proposal.

For each original sender input:

- outpoint remains;
- amount remains;
- sequence remains;
- sender ownership classification remains;
- proposal form is not finalized by the receiver.

## PJ-INV-02 — receiver inputs are explicit

At least one new receiver input must be added.

Every added receiver input must:

- be classified as receiver-owned by the local adapter;
- be finalized;
- carry UTXO information;
- contain no exposed keypaths;
- contain no partial signature field.

## PJ-INV-03 — version and locktime remain pinned

The proposal must preserve:

- transaction version;
- nLockTime.

## PJ-INV-04 — original input order remains

The v0.1 safety profile requires original sender inputs to remain in their original relative order.

Additional receiver inputs may be inserted.

## PJ-INV-05 — absolute fee never decreases

The proposal fee must be greater than or equal to the original absolute fee.

This follows the sender-side safety requirement of BIP 78.

## PJ-INV-06 — payment cannot shrink

The receiver payment amount may increase but must not decrease.

Output substitution is disabled by default.

If substitution is eventually enabled, the WAM adapter must independently prove the substituted output belongs to the intended receiver.

## PJ-INV-07 — sender outputs are protected

Every original non-payment sender output is immutable unless it is explicitly nominated as the sender's fee-contribution output.

A fee contribution:

- requires an explicit output index;
- requires an explicit maximum;
- cannot exceed that maximum.

## PJ-INV-08 — value-flow conservation

For the strict v0.1 profile:

```
receiver added input
=
receiver payment increase
+ proposal fee increase
- sender fee contribution
```

The validator checks this identity independently.

## PJ-INV-09 — no silent receiver batching yet

Full PayJoin may support unrelated receiver batching/cut-through.

WAM v0.1 intentionally does **not** claim support for this yet.

If the proposal adds outputs beyond the original output set, validation fails closed.

Reason: batching introduces a larger ownership/value-flow proof surface and should receive a separate invariant set.

## Output substitution

Default:

`allow_output_substitution = false`

This gives WAM a conservative baseline and also aligns with the need to avoid trusting an unverified transport/intermediary to redirect receiver outputs.

Support can be expanded after real PSBT integration exists.

## Relationship to BIP 77

BIP 77 adds asynchronous, encrypted message relay using an untrusted directory and OHTTP.

That transport architecture is attractive for WAM because sender and receiver need not be simultaneously online.

It is **not** implemented in Phase 4 v0.1.

The future sequence is:

```text
proposal safety
      ↓
real WAM PSBT adapter
      ↓
BIP-78-compatible synchronous prototype
      ↓
BIP-77 async transport research
```

## Real integration requirement

The current model contains normalized ownership fields.

Those fields must never be accepted from a remote peer as truth.

A real WAM adapter must derive:

- input ownership;
- output ownership;
- UTXO amounts;
- finalization state;
- keypath/partial-signature presence;
- version;
- locktime;
- sequence;
- fee;

from canonical local PSBT/transaction parsing.

## Exit gate

Phase 4 v0.1 passes internally when malicious proposal regressions cover:

- input removal;
- sequence mutation;
- version/locktime mutation;
- unauthorized output substitution;
- payment reduction;
- sender change theft;
- fee-contribution overflow;
- fee reduction;
- malformed receiver input metadata;
- hidden value-flow shifts;
- telemetry redaction.

Passing this gate does not establish BIP-78 or BIP-77 wire compatibility.
