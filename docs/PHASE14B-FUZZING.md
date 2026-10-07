# Phase 14B — Parser / Verifier Fuzzing and Adversarial Corpus

Phase 14B hardens the byte-facing verifier boundary before performance and release review.

## Scope

The phase separates two classes of testing:

1. **coverage-guided fuzzing**
   - canonical hardened-envelope decoder;
   - non-cryptographic verifier precheck: VK identity, context binding and transparent-balance binding.

2. **real-verifier adversarial corpus**
   - one cached real Phase 10D proof;
   - deterministic mutations of framing, canonical fields, VK identity, public balance, transaction context and proof bytes;
   - all mutations must fail closed with stable error classes and no panic.

The fuzz harness does not contact a node, wallet, public service or third-party system.

## Fuzz invariants

For arbitrary bytes:

- decode must never panic;
- any successfully decoded envelope must canonicalize and round-trip deterministically;
- precheck must never panic;
- malformed or ambiguous bytes must never become an accepted verifier relation;
- input length is bounded by the fuzz runner;
- crash artifacts, if any, are retained as CI evidence.

## Deterministic corpus

The seed generator archives representative cases:

- empty/truncated input;
- magic/header-only input;
- structurally canonical envelope with dummy proof bytes;
- trailing bytes;
- wrong instance count;
- non-canonical field encoding;
- oversized declared proof;
- unsupported version.

Corpus files are generated deterministically and bound by a SHA-256 manifest.

## Real verifier corpus

The real-proof adversarial test covers at minimum:

- valid control proof;
- wrong magic;
- unsupported version;
- wrong public-instance count;
- non-canonical field;
- wrong VK id;
- public fee mismatch;
- trailing/truncated bytes;
- transaction-context mismatch;
- tampered Halo2 proof.

Only the valid control may return success.

## Qualification

The CI gate uses:

- Rust stable 1.88 for format/clippy and deterministic tests;
- pinned nightly 2026-09-15 for libFuzzer;
- 100,000 executions per fuzz target;
- max fuzz input length 65,536 bytes;
- resource timeout/RSS guards;
- archived logs, corpus manifest and crash artifacts.

## Boundary

A 14B PASS is internal fuzzing evidence only. It is not proof of absence of parser/verifier vulnerabilities and does not replace independent review.
