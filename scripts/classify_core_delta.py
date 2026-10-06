#!/usr/bin/env python3
"""Classify WAM Core source drift relevant to the WSP qualification boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


HARD_PREFIXES = (
    "src/",
    "depends/",
    "cmake/",
)

HARD_FILES = {
    "CMakeLists.txt",
    "configure.ac",
    "Makefile.am",
}

REVIEW_PREFIXES = (
    "integration/",
    "scripts/",
    ".github/workflows/",
    "ops/",
)

KNOWN_NON_CORE_PREFIXES = (
    "pool/",
    "miner/",
    "explorer/",
    "site/",
    "posts/",
    "docs/",
)


def run(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout


def classify(path: str) -> str:
    if path in HARD_FILES or path.startswith(HARD_PREFIXES):
        return "hard-review-required"
    if path.startswith(REVIEW_PREFIXES):
        return "review"
    if path.startswith(KNOWN_NON_CORE_PREFIXES) or path == "SECURITY.md":
        return "outside-wsp-core-surface"
    return "unclassified-review"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    for rev in (args.baseline, args.target):
        run(args.repo, "cat-file", "-e", f"{rev}^{{commit}}")

    raw = run(args.repo, "diff", "--name-only", args.baseline, args.target)
    files = [line.strip() for line in raw.splitlines() if line.strip()]

    groups: dict[str, list[str]] = {
        "hard-review-required": [],
        "review": [],
        "outside-wsp-core-surface": [],
        "unclassified-review": [],
    }
    for path in files:
        groups[classify(path)].append(path)

    report = {
        "schema": 1,
        "baseline": args.baseline,
        "target": args.target,
        "changed_file_count": len(files),
        "classification": groups,
        "hard_gate": "FAIL" if groups["hard-review-required"] else "PASS",
        "meaning": (
            "PASS means no changed path entered the guarded WSP Core source/build surfaces; "
            "it is not proof of runtime compatibility."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

    if groups["hard-review-required"]:
        print("CORE_DRIFT_REQUIRES_EXPLICIT_REVIEW", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
