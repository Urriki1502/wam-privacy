# Phase 1 — WSP-1 Requalification Harness

This directory binds existing WSP-1 engineering work to exact source revisions.

## Why this exists

The Silent Payments implementation already exists in `wam-silent-payments`. Phase 1 is therefore a qualification problem, not a rewrite problem.

The harness answers three separate questions:

1. **Is the WSP implementation itself still internally green?**
2. **Did WAM Core change in source areas relevant to WSP assumptions?**
3. **Does the existing implementation still interoperate with the current WAM daemon on isolated regtest?**

Those questions have different evidence and must not be collapsed into one PASS label.

## Locked inputs

See [manifest.json](manifest.json).

Current pins:

- WSP: `a8522fee9b6eda285998a5ff4a45d6bc4eb991b3`
- previous qualified Core: `8a3f4fe4f1d804c378f795d4cc281ec5125f75f3`
- current Core target: `260bc468e5adffea7ce68d8f97fac3e27e4c50b2`

## Gate A — WSP contract

GitHub Actions runs:

- dependency installation from the WSP lock files;
- formatting/lint checks;
- `python -m devtools.selftest`;
- WSP black-box contract conformance.

This gate does not require a node and does not establish WAM Core compatibility.

## Gate B — Core drift classification

The target WAM Core revision is compared to the revision previously used by WSP qualification.

Changes under consensus/wallet/transaction build surfaces such as `src/` or `depends/` cause the automated drift gate to fail closed and require explicit review.

A clean drift gate means only:

> no source change was detected in the guarded surfaces.

It is not a proof of behavioral equivalence.

## Gate C — Current-Core isolated integration

This is the decisive compatibility gate.

It requires an exact WAM daemon build for the target commit and its SHA-256 digest. The existing WSP qualification harness then runs against private datadirs / loopback regtest.

Mandatory evidence includes:

- Core PSBT handoff;
- send / scan / confirm;
- restart;
- recovery;
- competing-chain reorgs;
- rollback and reconfirmation;
- final accounting.

The full local qualification command remains the existing WSP harness:

```bash
export WAMD=/absolute/path/to/wamd
export WAMD_SHA256=<sha256-of-that-exact-binary>
python scripts/qualify.py
```

## Gate D — protocol-sensitive qualification

If WSP protocol-sensitive code changes during requalification, rerun:

- 10,000-case independent differential testing;
- coverage-guided fuzzing;
- normative vectors;
- deterministic build checks.

If only WAM Core moves while the pinned WSP source is unchanged, these remain useful baseline evidence but Gate C is the compatibility-critical rerun.

## Status vocabulary

Only use:

- `PENDING`
- `PASS (internal engineering)`
- `FAIL`
- `BLOCKED — external review/adoption`

Do not label WSP production-ready while network-profile adoption and independent review remain unresolved.
