# Phase 4 Status — PayJoin Safety

| Gate | Status | Evidence |
| --- | --- | --- |
| Sender proposal-safety specification v0.1 | PASS | `docs/PAYJOIN-SAFETY.md` |
| Original input preservation | PASS | regression tests |
| Original sender input order | PASS | regression tests |
| Sequence preservation | PASS | regression tests |
| Version / locktime preservation | PASS | regression tests |
| Receiver input metadata checks | PASS | regression tests |
| Absolute fee non-decrease | PASS | regression tests |
| Payment non-decrease | PASS | regression tests |
| Sender output protection | PASS | regression tests |
| Explicit fee-contribution cap | PASS | regression tests |
| Strict value conservation profile | PASS | transaction balance + regression tests |
| Identifier/amount redaction | PASS | regression tests |
| Phase 4 CI | PASS (internal engineering) | workflow run `37468248558` |
| Real WAM PSBT adapter | NOT STARTED | separate future gate |
| BIP-78 wire transport | NOT STARTED | separate future gate |
| BIP-77 async transport | NOT STARTED | separate future gate |
| Production readiness | NOT CLAIMED | out of scope |

## Current claim

`PHASE 4 PAYJOIN SAFETY v0.1 — INTERNAL ENGINEERING PASS`

This establishes only the normalized sender-side safety policy.

It does not establish BIP-78/BIP-77 wire compatibility, real WAM PSBT parsing, or production PayJoin readiness.
