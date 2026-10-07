# Phase 13D — Resource / DoS Qualification

**Status:** under qualification.

Phase 13D adds explicit resource boundaries around the regtest-only Phase 13
integration before any broader Core experiment is considered.

## Threat model

The verifier and parser are computationally expensive surfaces. The research
integration must not allow malformed inputs or concurrent callers to create
unbounded work before basic fail-closed checks apply.

This phase evaluates:

- malformed/truncated proof envelopes;
- oversized declared proof lengths;
- per-block shielded transition count;
- concurrent access to the long-lived Halo2 verifier.

## Explicit limits

### Proof envelope

The Phase 10D envelope keeps the existing maximum proof-size bound.

The parser rejects an oversized declared proof before attempting to consume the
corresponding payload.

### Shielded transitions per modeled block

`MAX_TRANSITIONS_PER_BLOCK = 64`.

The state engine rejects a larger vector before publishing any state mutation.

This number is a research qualification cap, not a final consensus parameter.

### Verifier concurrency

The generated-Core wrapper owns one long-lived verifier instance and protects
it with a non-blocking mutex.

Behavior:

```text
first caller
    ↓
enters Halo2 verifier

concurrent caller
    ↓
try_lock fails
    ↓
BUSY
```

The second caller must not wait indefinitely or enter the expensive verifier.

## Qualification tests

Phase 13D requires:

- every truncated prefix of a canonical envelope fails closed;
- oversized declared proof length is rejected;
- deterministic malformed corpus does not decode;
- 65 modeled shielded transitions are rejected with no mutation;
- C++ concurrency smoke proves a second call returns `BUSY`;
- Rust formatting and clippy remain clean;
- all repository regression workflows remain green.

## Non-claims

Phase 13D does not set final production limits.

It does not provide:

- consensus transaction admission;
- mempool admission;
- production rate limiting;
- peer-level anti-DoS scoring;
- testnet/mainnet activation.

Those require WAM Core maintainer design and later hardening.

## Claim boundary

A Phase 13D PASS means the current research verifier/state integration has
explicit local resource gates and fail-closed concurrency behavior.

It does not mean the integration is production DoS-resistant.
