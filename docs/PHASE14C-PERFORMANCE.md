# Phase 14C — Proving / Verification Performance and Resource Baseline

Phase 14C records a reproducible CI baseline for the pinned Phase 10D hardened
2×2 Halo2 profile.

## Metrics

The dedicated benchmark records:

- parameter + VK/PK setup time;
- one real proof-generation time;
- three real verification samples (average and maximum);
- proof byte size;
- canonical envelope byte size;
- process peak RSS measured by GNU `/usr/bin/time -v`.

The benchmark target is built first. Peak RSS is then measured while executing
the already-built test process so compiler/linker memory is not mixed into the
verifier/prover profile.

## Qualification ceilings

The first qualification uses deliberately broad ceilings:

| Metric | Ceiling |
| --- | ---: |
| setup | 300 s |
| proof generation | 900 s |
| verification average | 120 s |
| verification maximum | 180 s |
| proof size | 4 MiB |
| encoded envelope | 4 MiB + 2 KiB |
| peak RSS | 6,000,000 KiB |

These are fail-closed regression ceilings, not performance targets.

A PASS means the current research profile remains within a bounded resource
envelope on the recorded GitHub runner. It does **not** claim production
latency, throughput, capacity or hardware sizing.

## Evidence

CI archives:

- `profile.json`;
- GNU-time resource log;
- benchmark stdout;
- normalized `evidence.json`;
- runner/toolchain identity.

The later Phase 14D ledger will bind the accepted 14C artifact digest.
