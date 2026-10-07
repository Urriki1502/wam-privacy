# Phase 15D — Independent Cryptographic / Circuit Review Intake

**Frozen candidate:** `00f8065c4f7b48fec01e4d97626ecbf2cc125852`

This document defines the minimum independent review contract for Phase 15D.
It is an intake specification, not a cryptographic-audit result.

## Reviewer profile

The reviewer should have applied cryptography and/or zero-knowledge circuit
review experience sufficient to assess Halo2-style constraint systems.

The final report must identify:

- reviewer name or stable pseudonym / organization;
- review date range;
- exact candidate commit;
- exact circuit/profile/VK identity reviewed;
- exact cryptographic dependencies/versions reviewed;
- methodology;
- findings and severity;
- unresolved assumptions;
- final disposition.

## Required review surfaces

At minimum inspect:

1. note commitment construction and domain separation;
2. nullifier construction and uniqueness/unlinkability assumptions;
3. authority-tag privacy/linkability assumptions;
4. spend/view key hierarchy and encoding;
5. range and monetary-cap constraints;
6. aggregate value-conservation constraints;
7. Merkle membership relation;
8. public/private witness binding and unconstrained witness risk;
9. transcript/proof configuration;
10. circuit/VK identity derivation;
11. serialization canonicality;
12. HPKE/AEAD note encryption usage;
13. context/network/transaction binding;
14. proof-verifier FFI assumptions.

## Explicit questions

The reviewer should answer explicitly:

- Can any private witness influence acceptance without being fully constrained?
- Can a field-modulus wraparound satisfy a value equation outside intended integer semantics?
- Can a proof valid in one network/version/transaction context replay in another?
- Can authority tags or any public derivation become a stable cross-note identifier?
- Can viewing capability authorize or derive spending authority?
- Can malformed note ciphertext or key material be interpreted ambiguously?
- Is the VK/circuit identity reproducible and bound to the verifier profile?
- Are domain separators unique across all cryptographic roles?

## Finding format

Each finding must include:

- ID: `CR-###`;
- severity: Critical / High / Medium / Low / Informational;
- affected cryptographic assumption/invariant;
- affected file/function/circuit;
- proof sketch / exploit condition / reasoning;
- impact;
- recommended remediation;
- regression/vector recommendation;
- status: Open / Confirmed / Disputed / Fixed / Accepted Risk.

## Exit rule

Phase 15D is PASS only when:

- an independent report covering the required scope is present;
- every Critical/High finding has a recorded disposition;
- confirmed Critical/High findings are remediated and requalified, or block handoff;
- the report is bound to the frozen candidate and circuit/VK profile.

Internal tests, fuzzing or the project author's own review cannot satisfy this gate.
