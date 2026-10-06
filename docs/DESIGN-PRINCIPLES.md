# Design Principles

## 1. Adapt, do not clone

WAM may learn from Bitcoin, Monero, Zcash, and other privacy systems, but each imported idea must be evaluated against WAM's own transaction model, consensus rules, wallet architecture, and operational constraints.

## 2. No custom cryptography by default

Use established primitives and published protocols whenever possible.

Novel cryptography is a last resort, not a branding feature.

## 3. Separate recognition from authority

A component that can recognize wallet activity should not automatically be able to authorize spending.

## 4. Least secret material

Each component receives only the secret material required for its role.

## 5. Fail closed

Malformed, incomplete, stale, or ambiguous security-critical state should produce an explicit error rather than a guessed success.

## 6. Recovery is a feature

Privacy metadata must remain recoverable from documented wallet secrets and canonical chain history wherever the protocol permits it.

## 7. Reorgs are normal

Any chain-indexed privacy state must define rollback and replay behavior from the beginning.

## 8. Privacy claims must be measurable

For every feature define:

- observer model;
- metadata reduced;
- metadata that remains visible;
- assumptions;
- known correlation channels.

## 9. Preserve supply integrity

Privacy must not weaken enforceable monetary-policy invariants.

## 10. Stage risk

Prefer application- and wallet-layer improvements before consensus-sensitive cryptography.

## 11. Hardware is an interface, not an architecture

Signer boundaries should permit software, offline, and future hardware implementations without redesigning wallet logic.

## 12. Tests are part of the protocol

Normative edge cases, negative cases, and deterministic vectors belong beside the specification, not as an afterthought.
