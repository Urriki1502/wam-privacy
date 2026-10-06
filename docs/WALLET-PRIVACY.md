# Phase 2 — Privacy-aware Wallet v0.1

**Status:** research prototype  
**Consensus impact:** none  
**Mainnet claim:** none

Phase 2 moves privacy policy into an explicit, testable wallet layer.

It does not require WSP-1 Gate C to be complete because this phase does not scan, sign, broadcast, or modify WAM Core. Integration into a production wallet remains blocked until the relevant lower-layer qualification gates are complete.

## Threat surface

A wallet can destroy privacy even when its address protocol is strong.

Typical failure modes include:

- combining unrelated UTXO clusters;
- creating unnecessary change;
- spending reserved or stale coins;
- logging addresses, txids, amounts, or stable wallet identifiers;
- non-deterministic policy that is difficult to reproduce and audit;
- silently falling back to a privacy-degrading selection when funds are fragmented.

Phase 2 treats these as explicit policy concerns.

## WP-INV-01 — cluster isolation by default

Coins assigned to different wallet-local clusters must not be merged implicitly.

If no single cluster can fund a payment, the default result is:

`INSUFFICIENT_SINGLE_CLUSTER_FUNDS`

Cross-cluster spending requires an explicit policy opt-in and produces the warning:

`CLUSTER_MERGE`

## WP-INV-02 — no dust change

A proposal must not create a positive change output below the configured dust threshold.

The reference policy prefers an exact/no-change construction when available.

## WP-INV-03 — deterministic decision

For identical:

- eligible coins;
- payment intents;
- fee;
- policy;

the selector must return the same selected outpoints regardless of input ordering.

This is important for reproducible testing and review.

## WP-INV-04 — reservations remain unavailable

Reserved coins and coins below the requested confirmation threshold are excluded before candidate construction.

The selector cannot silently override those states.

## WP-INV-05 — bounded search

Coin selection is attacker-influenced input.

The prototype therefore uses:

- bounded combination search;
- bounded maximum input count;
- deterministic greedy fallbacks.

It does not expose an unbounded subset-sum search surface.

## WP-INV-06 — telemetry minimization

Default operational telemetry must not contain:

- txids;
- vouts;
- recipient identifiers;
- cluster identifiers;
- exact payment/input/change amounts;
- stable cross-run wallet identifiers.

The reference `redacted_event()` reports only coarse operational properties.

## Selection ordering

Candidate selection is privacy-first and deterministic:

1. fewer clusters;
2. no change;
3. fewer inputs;
4. smaller change;
5. deterministic outpoint tie-break.

This is a policy choice, not a claim that one ordering is universally optimal for all threat models.

## Cluster model

A cluster is an **opaque wallet-local correlation group**.

Examples of future cluster inputs may include:

- user labels;
- account/sub-wallet boundaries;
- previously linked inputs;
- merchant/customer separation;
- treasury/operational separation.

The Phase 2 prototype deliberately does not implement heuristic chain clustering itself.

Why: automatically inferred clustering can be wrong, and a wrong inference should not silently become a spending authority decision.

## Change handling

This phase decides only whether change is required.

Actual change-address construction remains protocol-specific and must eventually integrate with:

- WSP private change policy where applicable;
- signer validation;
- wallet recovery metadata.

## Integration boundary

```text
Chain / scanner
      │
      ▼
eligible wallet coins
      │
      ▼
Privacy Policy  ← Phase 2
      │
      ├── selected coins
      ├── explicit warnings
      └── change requirement
      │
      ▼
Transaction builder
      │
      ▼
Signer boundary
```

The policy layer does not hold spend secrets.

## Exit gate

Phase 2 v0.1 passes internally when:

- deterministic reference implementation exists;
- cluster merge is opt-in;
- dust change fails closed;
- reservation/confirmation filtering is tested;
- telemetry redaction is tested;
- CI executes the reference suite.

Production integration is a separate future gate.
