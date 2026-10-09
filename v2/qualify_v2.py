#!/usr/bin/env python3
"""WAM Privacy V2-05 reproducible research evidence index.

This script verifies that a clean, pinned V2-05 checkout carries exactly the
29 specified acceptance IDs, cites existing source/fixture evidence honestly,
preserves frozen V1 code and does not self-certify external audit, production
security, Core activation or real network privacy. It does not use sockets.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

V1 = "95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127"
V2_04 = "f7914ef9ee9815c573f5bf5c08dc9785deeee231"
WSP = "dcf1aecc00a64bfad3151fa202c3e07d47d83e69"
CORE = "260bc468e5adffea7ce68d8f97fac3e27e4c50b2"
PREFIX_COUNTS = {"CAP": 10, "FLOW": 8, "NET": 4, "CORE": 3, "PERF": 2, "COMPAT": 2}
CLASSES = {
    "FIXTURE_ONLY", "REGTEST_SIGNER", "V1_REGRESSION_ONLY",
    "SOURCE_GUARD_ONLY", "PARTIAL", "BLOCKED",
}
FROZEN_PATHS = (
    "prototypes/zk_balance_halo2/", "integration/core/", "tests/",
    "scripts/phase14d_static_review.py", "scripts/build_phase14d_ledger.py",
)
ONLY_V2_05_ALLOWED = (
    "v2/", "docs/v2/", ".github/workflows/v2-",
    "scripts/run_phase15f_v1_final_audit.py",
    "scripts/build_phase15_review_package.py",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("V2_05_REJECTED: " + message)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_ids() -> set[str]:
    return {
        f"{prefix}-{number:03d}"
        for prefix, size in PREFIX_COUNTS.items()
        for number in range(1, size + 1)
    }


def validate_matrix(raw: object, root: Path) -> dict[str, object]:
    require(isinstance(raw, dict), "matrix object")
    require(set(raw) == {
        "schema", "spec_reference", "stage", "source_v1_pin",
        "source_v2_04_head", "statuses", "claims", "cases",
    }, "matrix schema")
    require(raw["schema"] == 1 and raw["stage"] == "V2-05-RESEARCH-ONLY",
            "version/stage drift")
    require(raw["source_v1_pin"] == V1 and raw["source_v2_04_head"] == V2_04,
            "pinned source drift")
    require(set(raw["statuses"]) == CLASSES
            and len(raw["statuses"]) == len(CLASSES), "status vocabulary drift")
    require(raw["claims"] == {
        "production": False, "external_audit": False, "mainnet_activation": False
    }, "forbidden security claim")
    cases = raw["cases"]
    require(isinstance(cases, list) and len(cases) == 29, "29 cases required")
    ids = [c.get("id") for c in cases if isinstance(c, dict)]
    require(len(ids) == 29 and len(set(ids)) == 29
            and set(ids) == expected_ids(), "missing/duplicate/unexpected case IDs")
    classes: Counter[str] = Counter()
    paths: set[str] = set()
    for case in cases:
        require(set(case) == {
            "id", "summary", "evidence_class", "evidence_paths",
            "evidence_tests", "limitation",
        }, "case schema: " + case["id"])
        label = case["id"]
        cls = case["evidence_class"]
        require(cls in CLASSES, "unknown class: " + label)
        classes[cls] += 1
        require(type(case["summary"]) is str and 10 <= len(case["summary"]) <= 256,
                "invalid summary: " + label)
        require(type(case["limitation"]) is str and 12 <= len(case["limitation"]) <= 400,
                "missing explicit limitation: " + label)
        evidence = case["evidence_paths"]
        tests = case["evidence_tests"]
        require(type(evidence) is list and 1 <= len(evidence) <= 4
                and len(set(evidence)) == len(evidence), "evidence paths: " + label)
        require(type(tests) is list and len(tests) <= 4, "evidence tests: " + label)
        require(cls != "BLOCKED" or label == "CORE-003",
                "unexpected production block downgrade")
        require(label != "CORE-003" or cls == "BLOCKED",
                "CORE-003 must remain blocked")
        for rel in evidence:
            require(type(rel) is str and re.fullmatch(r"[a-zA-Z0-9_./-]+", rel)
                    and not rel.startswith("/") and ".." not in rel.split("/"),
                    "unsafe evidence path: " + label)
            require((root / rel).is_file(), "missing evidence: " + rel)
            paths.add(rel)
        # Test references must resolve to functions in the cited source file,
        # not free-text placeholders. Some V1 proof tests are in Rust files.
        source = "\n".join((root / rel).read_text(encoding="utf-8") for rel in evidence)
        for symbol in tests:
            require(type(symbol) is str and re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", symbol),
                    "invalid test symbol: " + label)
            require(re.search(r"\b(?:def|fn)\s+" + re.escape(symbol) + r"\s*\(", source)
                    is not None, "test symbol not found: " + label + ":" + symbol)
    require(classes["BLOCKED"] >= 1, "must preserve unresolved CORE-003")
    return {"cases": len(cases), "categories": dict(sorted(classes.items())),
            "evidence_paths": sorted(paths)}


def check_source(root: Path, peer: Path) -> str:
    require(root.is_dir() and peer.is_dir() and root.resolve() != peer.resolve(),
            "need two independent checkout paths")
    head_a, head_b = git(root, "rev-parse", "HEAD"), git(peer, "rev-parse", "HEAD")
    require(bool(re.fullmatch(r"[0-9a-f]{40}", head_a)) and head_a == head_b,
            "checkout HEAD mismatch")
    require(not git(root, "status", "--porcelain")
            and not git(peer, "status", "--porcelain"), "dirty checkout")
    require(git(root, "rev-parse", "HEAD^{tree}") ==
            git(peer, "rev-parse", "HEAD^{tree}"), "independent source trees mismatch")
    for ancestor in (V1, V2_04):
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                        ancestor, "HEAD"], check=True, capture_output=True)
    v1_paths = git(root, "diff", "--name-only", V1, "HEAD", "--", *FROZEN_PATHS)
    require(not v1_paths, "frozen V1 implementation changed: " + v1_paths)
    changed = git(root, "diff", "--name-only", V2_04, "HEAD").splitlines()
    require(all(any(f == a or f.startswith(a) for a in ONLY_V2_05_ALLOWED)
                for f in changed), "V2-05 scope drift")
    return head_a


def create_report(root: Path, peer: Path) -> dict[str, object]:
    head = check_source(root, peer)
    matrix_path = root / "v2/acceptance_matrix.json"
    raw = json.loads(matrix_path.read_text(encoding="utf-8"))
    summary = validate_matrix(raw, root)
    other = json.loads((peer / "v2/acceptance_matrix.json").read_text(encoding="utf-8"))
    require(raw == other, "independent clone acceptance matrix differs")
    inputs = set(summary["evidence_paths"]) | {
        "v2/acceptance_matrix.json", "v2/qualify_v2.py",
        "docs/v2/V2-05-REVIEW-HANDOFF.md",
        ".github/workflows/v2-05-qualification.yml",
        "prototypes/zk_balance_halo2/Cargo.lock",
        "prototypes/zk_balance_halo2/rust-toolchain.toml",
    }
    fingerprints: dict[str, str] = {}
    for path in sorted(inputs):
        require((root / path).is_file() and (peer / path).is_file(),
                "missing pin input: " + path)
        h = sha256(root / path)
        require(h == sha256(peer / path), "hash mismatch: " + path)
        fingerprints[path] = h
    return {
        "schema": 1,
        "result": "REPRODUCIBLE_RESEARCH_EVIDENCE_INDEX_ONLY",
        "production": "BLOCKED",
        "mainnet_activation": "NOT_AUTHORIZED",
        "independent_cryptographic_audit": "PENDING_EXTERNAL",
        "independent_state_machine_audit": "PENDING_EXTERNAL",
        "root_derivation_core_003": "BLOCKED",
        "wallet_crash_safe_persistence": "NOT_IMPLEMENTED",
        "real_transport_anonymity": "NOT_ESTABLISHED",
        "qualified_checkout_head": head,
        "frozen_v1_source": V1,
        "qualified_v2_04_parent": V2_04,
        "wsp_source_pin": WSP,
        "core_reference_pin": CORE,
        "independent_clean_checkout_count": 2,
        "case_summary": summary,
        "input_sha256": fingerprints,
        "ci_verdict": "NOT_SELF_ATTESTED_CHECK_GITHUB_ACTIONS_AT_EXACT_HEAD",
        "no_tag_or_release": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--peer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = create_report(args.root.resolve(), args.peer.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "commit": report["qualified_checkout_head"],
        "acceptance_cases": report["case_summary"]["cases"],
        "production": report["production"],
        "CORE-003": report["root_derivation_core_003"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
