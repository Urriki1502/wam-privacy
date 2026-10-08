#!/usr/bin/env python3
"""Phase 15B extended isolated-regtest drill orchestrator.

This script deliberately exercises the frozen implementation through existing
qualification tests. It does not modify protocol/circuit/wallet/Core code and
does not claim public-testnet history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone


FROZEN_BASELINE = "8bfbced65299a8491345b54b38bff0db498b618d"
PHASE15A_LEGACY_MERGE = "e5d436a201d3fdf26f2a6bb2ea750be8ce213aab"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True
    ).strip()


def run_step(
    *,
    name: str,
    argv: list[str],
    cwd: Path,
    log_path: Path,
) -> dict:
    started = time.monotonic()
    with log_path.open("wb") as log:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    elapsed = time.monotonic() - started
    return {
        "name": name,
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": proc.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "log": str(log_path),
        "log_sha256": sha256(log_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--proof-every", type=int, default=2)
    ap.add_argument("--pause-seconds", type=float, default=0.0)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    if args.rounds < 1:
        raise SystemExit("--rounds must be >= 1")
    if args.proof_every < 0:
        raise SystemExit("--proof-every must be >= 0")
    if args.pause_seconds < 0:
        raise SystemExit("--pause-seconds must be >= 0")

    root = args.root.resolve()
    crate = root / "prototypes/zk_balance_halo2"
    if not (crate / "Cargo.toml").is_file():
        raise SystemExit(f"missing Halo2 crate: {crate}")

    # Verify the corrected Phase 14-requalified source candidate exists.
    # Only Phase 15 review/qualification metadata may differ after this SHA.
    # The Phase 15A historical merge proves lineage only, not qualification.
    git(root, "cat-file", "-e", f"{FROZEN_BASELINE}^{{commit}}")
    git(root, "cat-file", "-e", f"{PHASE15A_LEGACY_MERGE}^{{commit}}")
    head = git(root, "rev-parse", "HEAD")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    log_dir = output.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    records: list[dict] = []
    failed = False
    real_proof_rounds = 0

    cheap_steps = [
        (
            "wallet-recovery-reorg",
            ["cargo", "test", "--locked", "--test", "wallet_state", "--", "--nocapture"],
            crate,
        ),
        (
            "core-deep-reorg-300",
            [
                "cargo",
                "test",
                "--locked",
                "core_state::tests::deep_reorg_300_blocks_restores_and_replays",
                "--",
                "--exact",
                "--nocapture",
            ],
            crate,
        ),
        (
            "generated-core-hook-contract",
            ["python3", "-m", "unittest", "tests.test_phase13b_generated_core", "-v"],
            root,
        ),
    ]

    proof_steps = [
        (
            "real-proof-to-core-state",
            ["cargo", "test", "--locked", "--test", "core_state_proof", "--", "--nocapture"],
            crate,
        ),
        (
            "real-proof-through-c-abi",
            ["cargo", "test", "--locked", "--test", "ffi_bridge", "--", "--nocapture"],
            crate,
        ),
    ]

    completed_rounds = 0
    for round_no in range(1, args.rounds + 1):
        round_record = {"round": round_no, "steps": []}

        for step_index, (name, argv, cwd) in enumerate(cheap_steps, start=1):
            log_path = log_dir / f"round-{round_no:04d}-{step_index:02d}-{name}.log"
            result = run_step(name=name, argv=argv, cwd=cwd, log_path=log_path)
            round_record["steps"].append(result)
            if result["exit_code"] != 0:
                failed = True
                break

        run_proofs = (
            not failed
            and args.proof_every > 0
            and (round_no % args.proof_every == 0 or round_no == args.rounds)
        )
        if run_proofs:
            real_proof_rounds += 1
            offset = len(cheap_steps)
            for proof_index, (name, argv, cwd) in enumerate(proof_steps, start=1):
                log_path = (
                    log_dir
                    / f"round-{round_no:04d}-{offset + proof_index:02d}-{name}.log"
                )
                result = run_step(name=name, argv=argv, cwd=cwd, log_path=log_path)
                round_record["steps"].append(result)
                if result["exit_code"] != 0:
                    failed = True
                    break

        records.append(round_record)
        if failed:
            break

        completed_rounds = round_no
        if round_no != args.rounds and args.pause_seconds:
            time.sleep(args.pause_seconds)

    finished_at = datetime.now(timezone.utc)
    all_steps = [step for record in records for step in record["steps"]]
    successful_steps = sum(step["exit_code"] == 0 for step in all_steps)

    report = {
        "schema": 1,
        "stage": "phase-15b-extended-regtest-drill-harness",
        "network_mode": "isolated-regtest-research",
        "public_testnet_history": False,
        "frozen_internal_baseline": FROZEN_BASELINE,
        "phase15a_prior_merge": PHASE15A_LEGACY_MERGE,
        "qualification_head": head,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "requested_rounds": args.rounds,
        "completed_rounds": completed_rounds,
        "proof_every": args.proof_every,
        "real_proof_rounds": real_proof_rounds,
        "pause_seconds": args.pause_seconds,
        "drill_counts": {
            "wallet_restart_recovery_reorg_suites": sum(
                s["name"] == "wallet-recovery-reorg" and s["exit_code"] == 0
                for s in all_steps
            ),
            "deep_300_block_reorg_suites": sum(
                s["name"] == "core-deep-reorg-300" and s["exit_code"] == 0
                for s in all_steps
            ),
            "generated_core_contract_suites": sum(
                s["name"] == "generated-core-hook-contract" and s["exit_code"] == 0
                for s in all_steps
            ),
            "real_proof_core_state_suites": sum(
                s["name"] == "real-proof-to-core-state" and s["exit_code"] == 0
                for s in all_steps
            ),
            "real_proof_ffi_suites": sum(
                s["name"] == "real-proof-through-c-abi" and s["exit_code"] == 0
                for s in all_steps
            ),
        },
        "successful_steps": successful_steps,
        "total_steps": len(all_steps),
        "rounds": records,
        "result": "PASS_HARNESS_DRILL" if not failed and completed_rounds == args.rounds else "FAIL",
        "non_claims": [
            "not public-testnet history",
            "not independent review",
            "not production readiness",
            "not mainnet readiness",
            "not consensus activation",
        ],
    }

    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS_HARNESS_DRILL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
