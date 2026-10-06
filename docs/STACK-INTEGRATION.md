# Phase 6 — Privacy Stack Integration Contract v0.1

**Status:** normalized integration prototype  
**Real WAM adapter:** not implemented  
**Consensus impact:** none

Phases 2–5 each established a local invariant set. Phase 6 verifies that those
invariants remain true **when the layers are composed**.

## Stack

```text
Privacy-aware coin selection
            │
            ▼
   original transaction
            │
            ▼
     PayJoin validator
            │
            ▼
    network route gate
            │
            ▼
       SignerGate
            │
            ▼
   signing provider fixture
```

No real transaction is signed or transmitted by this phase.

## Why integration is a separate gate

A component can be correct in isolation while two correct components disagree
about semantics.

Phase 6 found one such boundary:

- PayJoin permits a receiver-funded increase to the receiver payment output.
- The original signer abstraction required exact payment-output equality.

Rejecting all such proposals would make the layers incompatible. Blindly
accepting increased outputs would weaken signer approval.

The integration rule is therefore:

> A PayJoin payment increase is accepted only when PayJoin is explicitly
> approved, payment increase is explicitly approved, and the sender's actual
> wallet debit remains within original intent value + user-approved fee.

## SI-INV-01 — wallet selection binds original inputs

The normalized original sender inputs must exactly match the Phase 2 selected
outpoints and values.

A later layer cannot silently substitute wallet coins.

## SI-INV-02 — original economic intent binds before PayJoin

Before proposal processing:

- original receiver destination equals the approved intent;
- original receiver amount equals the approved intent;
- original fee is within approval;
- original change agrees with Phase 2 selection.

## SI-INV-03 — warning propagation is lossless

Phase 2 warnings are propagated to the signer.

Examples:

- `CLUSTER_MERGE`
- `CHANGE_CREATED`

Phase 6 adds:

- `PAYJOIN_PROPOSAL`

Warnings are not merely UI decoration. They are authorization inputs.

## SI-INV-04 — PayJoin cannot increase sender debit silently

For a PayJoin signing request the signer receives the locally derived total
wallet-input value.

It computes:

```
sender debit = wallet input value - verified wallet change
```

and requires:

```
sender debit <= approved payment intents + approved sender fee
```

The total transaction fee may be larger when receiver inputs fund it, but it
remains bounded by the signer's hard transaction-fee policy.

## SI-INV-05 — network route validates before signing

A private-route policy failure occurs before the signing provider is called.

This prevents creation of an approved signature when the current plan would
immediately require a privacy downgrade to broadcast it.

This is still only a policy guarantee; a future runtime must revalidate the
route at broadcast time to prevent time-of-check/time-of-use drift.

## SI-INV-06 — PayJoin safety precedes signing

Input/output mutation failures detected by Phase 4 stop the pipeline before the
signer provider is called.

## SI-INV-07 — coarse telemetry only

Cross-layer telemetry contains no:

- txids/outpoints;
- destinations;
- exact amounts;
- hostnames/IPs/ports;
- request IDs;
- transaction digests;
- key/device identifiers.

## Current limitations

v0.1 intentionally supports a narrow normalized profile:

- one payment intent;
- at most one sender change output;
- strict Phase 4 PayJoin output model;
- regtest signer fixture;
- no actual PSBT parsing;
- no socket/network implementation;
- no real cryptographic signing.

These constraints make the integration invariants auditable before the real WAM
adapter is introduced.

## Next gate

After this integration contract passes, the next high-value implementation step
is a **real WAM PSBT/transaction adapter** that derives these normalized facts
from canonical bytes and local wallet ownership state.

That adapter remains blocked from production claims until Phase 1 WSP current-
Core runtime qualification is closed.
