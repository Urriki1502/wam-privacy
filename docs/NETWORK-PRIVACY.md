# Phase 5 — Network Privacy v0.1

**Status:** policy/reference prototype  
**Networking implementation:** none  
**Consensus impact:** none

A private address or PayJoin transaction can still leak useful metadata if wallet traffic directly identifies the user's network origin.

Phase 5 therefore separates three concepts:

1. **transport encryption**;
2. **route privacy**;
3. **role separation**.

They are not interchangeable.

## NP-INV-01 — local chain scan by default

The default chain source is a locally validating node over loopback.

Remote scan backends require explicit opt-in because a remote backend can observe wallet-interest queries.

## NP-INV-02 — private transaction broadcast

When private broadcast is required, a direct public route is rejected.

Accepted route classes in the v0.1 policy are:

- Tor;
- I2P;
- OHTTP-mediated route where appropriate.

This is a policy classification, not a claim that every use of those transports provides equivalent anonymity.

## NP-INV-03 — encryption is not anonymity

A direct encrypted connection remains a direct network-origin relationship.

BIP 324 is an important reference for opportunistic encrypted P2P transport, but transport encryption alone does not hide the sender's IP/network path.

The policy therefore models:

`encrypted_transport`

separately from:

`route`

A direct encrypted broadcast still fails when private routing is mandatory.

## NP-INV-04 — no silent clearnet fallback

If a private route fails, v0.1 does not silently downgrade to direct clearnet.

A direct fallback requires explicit policy.

This avoids turning temporary Tor/I2P failure into an invisible privacy failure.

## NP-INV-05 — async PayJoin directory path

When Async PayJoin mode is enabled, the v0.1 policy requires an OHTTP-class directory route.

This mirrors the privacy objective of BIP 77: the directory should not trivially link client network origin to mailbox activity.

No BIP-77 transport implementation exists in this phase.

## NP-INV-06 — public role separation

A single public endpoint should not simultaneously become:

- wallet scan backend;
- transaction broadcast endpoint;
- PayJoin directory;

because role reuse increases correlation opportunity.

Local loopback plumbing is exempt.

## NP-INV-07 — telemetry minimization

Network telemetry must not contain:

- hostnames;
- IP addresses;
- onion/I2P service names;
- ports;
- credentials;
- proxy usernames;
- stable endpoint identifiers.

The reference helper emits only route class and coarse result metadata.

## Architecture

```text
                  Wallet
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
   chain scan   tx broadcast   PayJoin
        │           │            │
   local node    Tor / I2P     OHTTP
        │
        ▼
    WAM Core
```

This is a privacy policy shape, not a final deployment topology.

## BIP 324 position

BIP 324 is a deployed Bitcoin reference for v2 encrypted P2P transport.

For WAM it is useful as a research reference for:

- opportunistic encryption;
- forward secrecy;
- transport negotiation;
- passive-eavesdropping resistance.

It must not be presented as an anonymity layer.

## Exit gate

Phase 5 v0.1 passes internally when tests prove:

- local scan is default;
- remote scan is opt-in;
- encrypted direct broadcast does not satisfy private-route policy;
- direct fallback fails closed;
- async PayJoin requires OHTTP-class routing;
- public endpoint role reuse is rejected;
- telemetry contains no endpoint identity.

Actual Tor/I2P/OHTTP/BIP324 implementation remains a later integration phase.
