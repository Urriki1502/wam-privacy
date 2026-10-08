# Phase 15B — Extended Regtest / Testnet Drill Harness

**Status:** under qualification.

Phase 15B qualifies the long-run drill machinery that will be used to collect
extended regtest and later operator-managed testnet evidence for the frozen
Phase 14D candidate.

## Freeze boundary

The corrected, internally requalified source candidate is:

`8bfbced65299a8491345b54b38bff0db498b618d`

The superseded source baseline `00f8065c4f7b48fec01e4d97626ecbf2cc125852` is historical only.
The prior Phase 15B PASS is not evidence for this corrected candidate;
a fresh isolated-regtest drill must pass.

Phase 15B changes only qualification scripts, workflows, documentation and
evidence metadata. It does not modify protocol, circuit, wallet, verifier,
Core-integration or cryptographic code.

## Drill composition

Each drill round executes the existing frozen regression paths:

1. shielded wallet scanning / restart / recovery / reorg suite;
2. Core shielded-state deep 300-block rollback/replacement replay;
3. generated-Core hook contract tests.

At the configured proof cadence the harness additionally executes:

4. a real Phase 10D proof driving the Core shielded-state transition path;
5. a real Phase 10D proof through the Core-facing C ABI.

Every command records:

- exit code;
- elapsed time;
- command line;
- working directory;
- SHA-256 of its complete log.

The final JSON report binds the frozen baseline, Phase 15A merge, qualification
head, round count, proof cadence and every log digest.

## CI versus extended execution

The GitHub workflow intentionally runs only a short deterministic smoke drill.
Its purpose is to prove that the harness itself is reproducible and operational.

A recommended longer isolated run is:

```bash
python3 scripts/run_phase15b_extended_drill.py \
  --root . \
  --rounds 288 \
  --proof-every 24 \
  --pause-seconds 300 \
  --output reports/phase15b/extended-24h.json
```

That approximates a 24-hour operator drill while periodically exercising the
expensive real-proof path.

## Public testnet boundary

A short CI run or an isolated long-run drill is **not** public-testnet history.

Before final handoff, an operator-managed testnet record must separately bind:

- exact WAM/privacy commits and binary hashes;
- network parameters;
- start/end time and heights;
- shield / transfer / unshield counts;
- verifier accept/reject counts;
- malformed-proof and duplicate-nullifier rejection;
- restart/recovery drills;
- short/deep reorg drills;
- replay-equivalent state/pool balance;
- resource observations;
- incidents and remediation.

Use `qualification/PHASE15B-TESTNET-TEMPLATE.json` as the evidence schema.

## Exit gate

Phase 15B harness qualification passes when:

- the Phase 15A freeze validator still passes;
- the smoke drill completes all requested rounds;
- deep-reorg and wallet-recovery suites pass in every round;
- the real-proof Core-state and C-ABI paths pass at least once;
- a machine-readable drill report and hashed logs are uploaded;
- public-testnet work remains explicitly unclaimed.

## Claim

Passing Phase 15B means **extended-drill harness ready**.

It does not satisfy the independent-review or public-testnet requirements of
Phase 15 completion.
