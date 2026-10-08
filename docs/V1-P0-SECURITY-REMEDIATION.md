# WAM Privacy V1 — P0 Remediation (internal engineering)

Status: **IN PROGRESS — do not freeze/tag or claim production readiness**.

## Confirmed source-level finding: unconstrained domain separator advice

In both Phase 10B and Phase 10D bundle circuits, the Poseidon domain
separator cells for note commitments, spend authority tags and nullifiers
were assigned with `assign_advice(... Value::known(Fp::from(DOMAIN)))`
rather than bound through fixed constant equality constraints. While the
honest prover fills these cells with intended constants, the circuit
relation must independently prevent a malicious prover from choosing
a different witness.

Fix: `assign_advice_from_constant` for four domain assignments per
bundle circuit, including the output note domain. The fixed-column
configuration was already present in both circuits.

Evidence targets:
- static regression asserts all four fixed assignments per profile;
- legacy and hardened bundle MockProver negative cases;
- real Halo2 proof generation and verification;
- context, VK identity and cross-version rejection;
- complete Phase 14 replay and updated qualification evidence.

These changes may alter verifying-key identity. The previous
Phase 14D candidate `00f8065c4f7b48fec01e4d97626ecbf2cc125852`
must **not** be reused as the corrected source baseline.

## Confirmed integration trust-boundary finding: fabricated verified transitions

Prior `VerifiedTransition` had public fields and callers could construct
or mutate an accepted-looking transition without presenting any verified
proof. The regtest Core state model consumed this object without re-running
verification at the `apply_block` boundary.

Fix: make all `VerifiedTransition` fields private and expose a read-only
anchor accessor. External transition construction is restricted to
`from_verified_envelope`, which verifies the canonical proof first.
A `compile_fail` doc test guards against reintroducing public struct
construction. The existing malformed proof negative test remains.

**Residual trust boundary:** `StateBlock::next_anchor` is supplied by the
higher-level commitment-tree integration, which does **not yet** implement
a production canonical-tree root transition. The model remains research /
regtest only; production integration must derive and validate the ordered
tree root from canonical outputs, not accept a caller-supplied root.

## Remediation release criteria

1. Full Rust tests, doc tests, Clippy, FFI and WAM Core regtest gates PASS.
2. Domain separator regression and proof verification tests PASS.
3. New source commit and VK identity are pinned with fresh Phase 14 evidence.
4. Phase 15 material and freeze validation are rebased on the new candidate.
5. Independent Phase 15C/15D reviewer reports remain pending and must
   not be marked PASS internally.
6. No tag `v1.0.0` or mainnet-readiness claim before qualification and
   release policy are satisfied.

Review requests can be prepared and bundled for the WAM maintainer after
V2 development, as the project owner requested, but the missing external
review remains explicitly recorded throughout.
