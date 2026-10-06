# Phase 3 — Signer Abstraction v0.1

**Status:** research/reference contract  
**Cryptographic signing:** not implemented here  
**Consensus impact:** none

Phase 3 defines a narrow signing boundary so wallet logic does not depend on one key store, one hardware vendor, or one process model.

## Objective

```text
Wallet / transaction builder
          │
          ▼
   normalized request
          │
          ▼
      SignerGate
   ┌──────┼────────┐
   ▼      ▼        ▼
Software Offline Hardware
Signer   Signer   Signer
```

The gate owns policy validation.

A provider owns the mechanics of signing.

A provider must not be called until the request satisfies the independent approval policy.

## SA-INV-01 — no implicit signing

A wallet request is not sufficient by itself.

The gate also requires an explicit `Approval` describing:

- approved recipient/amount intents;
- maximum fee;
- whether cluster merge is explicitly approved.

## SA-INV-02 — payment intent equivalence

The payment outputs in the normalized transaction view must exactly match the approved payment-intent multiset.

Additional payment outputs fail closed.

## SA-INV-03 — change must be independently classified

A change output must be marked wallet-owned by the future WAM transaction adapter.

The generic reference model does not infer ownership from an address string.

Integration rule:

> the adapter that parses real WAM transaction bytes must independently prove wallet change ownership before setting `wallet_owned=True`.

## SA-INV-04 — warning acknowledgement

Unknown warning codes fail closed.

`CLUSTER_MERGE` requires explicit approval.

`CHANGE_CREATED` must agree with the normalized transaction view.

## SA-INV-05 — policy cap beats user approval

A user approval cannot override hard signer policy.

Example:

- user approves fee <= 1000;
- signer policy hard cap = 500;
- fee 600 is rejected.

## SA-INV-06 — replay after successful signing

Within one signer-gate session, a completed request ID cannot be signed a second time.

Provider failure or malformed provider output does not mark the request complete, allowing controlled retry.

Persistent anti-replay across process restarts is a future integration requirement.

## SA-INV-07 — provider result binding

A provider result must bind to the same:

- request ID;
- transaction digest.

A mismatched result is rejected.

## Provider capabilities

Every signer reports:

- kind: software / offline / hardware / fixture;
- supported networks;
- whether it is intended for production.

The included `FixtureSigner` is explicitly:

`production=False`

and produces no real WAM signature.

## Hardware signer position

YubiKey or another hardware-backed signer is **not required** for this phase.

The architecture intentionally makes hardware a provider implementation rather than a wallet redesign.

Future options may include:

- hardware wallet;
- secure element;
- HSM;
- offline air-gapped signer.

Selection should happen only after the WAM transaction/signing adapter is stable.

## Real WAM integration requirements

Before any provider signs actual WAM transactions, an adapter must:

1. parse canonical transaction/PSBT bytes;
2. derive the transaction digest from those bytes;
3. derive payment outputs and fee independently;
4. prove change ownership;
5. map wallet privacy warnings;
6. create the normalized `SignRequest`;
7. compare it against explicit approval;
8. invoke the provider only after validation.

The caller must not be trusted to supply those fields without independent derivation.

## Telemetry

Default signer telemetry excludes:

- request ID;
- tx digest;
- destinations;
- exact amounts;
- provider serial/device identifier;
- key identifiers.

Only coarse operational fields are retained by the reference telemetry helper.

## Exit gate

Phase 3 v0.1 passes internally when:

- provider protocol exists;
- validation gate exists;
- policy/approval separation is tested;
- replay semantics are tested;
- provider failure semantics are tested;
- result binding is tested;
- telemetry redaction is tested;
- CI passes.

Production cryptographic signing remains out of scope.
