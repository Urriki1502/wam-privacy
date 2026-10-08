# Phase 15C — Independent State-Machine Review Intake

**Current internally requalified source candidate (review still pending):** `8bfbced65299a8491345b54b38bff0db498b618d`

Earlier candidate `00f8065c4f7b48fec01e4d97626ecbf2cc125852` is superseded; no independent review has been completed.

This document defines the minimum independent review contract for Phase 15C.
It is an intake specification, not a review result.

## Reviewer independence

The reviewer must not be the author of the reviewed implementation or the agent
that produced the internal qualification evidence.

The final report must identify:

- reviewer name or stable pseudonym / organization;
- review date range;
- exact candidate commit;
- exact WAM Core dependency/profile reviewed;
- files/modules actually reviewed;
- methods used;
- findings and severity;
- unresolved assumptions;
- final disposition.

## Required review surfaces

At minimum inspect:

1. shielded state transition model;
2. note commitment / nullifier semantics;
3. bundle value conservation;
4. transparent/shielded balance binding;
5. duplicate-nullifier handling;
6. commitment-tree append semantics;
7. atomic acceptance/state mutation;
8. disconnect/reconnect behavior;
9. deep reorg rollback/replay;
10. wallet scanning/recovery equivalence;
11. version/network context binding;
12. Core/verifier failure boundary.

## Required invariants to attempt to falsify

- no accepted transition can create net value;
- one nullifier cannot be accepted twice;
- rejected proof/encoding cannot partially mutate state;
- reorg rollback restores the exact prior canonical state;
- replay of the replacement chain converges to one deterministic state;
- transparent in/out/fee cannot diverge from the proof-bound context;
- wallet recovery from canonical history reconstructs equivalent spendable state;
- unsupported network/version/profile fails closed.

## Finding format

Each finding must include:

- ID: `SMR-###`;
- severity: Critical / High / Medium / Low / Informational;
- affected invariant;
- affected file/function or protocol rule;
- minimal counterexample or reasoning;
- impact;
- recommended fix;
- regression-test recommendation;
- status: Open / Confirmed / Disputed / Fixed / Accepted Risk.

## Exit rule

Phase 15C is PASS only when:

- an independent report covering the required scope is present;
- every Critical/High finding has a recorded disposition;
- confirmed Critical/High findings are either remediated with regression evidence
  or explicitly block handoff;
- the report is bound to the frozen candidate commit.

Self-review or internal CI cannot satisfy this gate.
