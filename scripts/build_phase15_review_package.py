#!/usr/bin/env python3
"""Build and validate the Phase 15A external-review package manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASELINE = "15fafa199871f7a1688b1beda5e27005ae473d27"

REQUIRED = [
    "ARCHITECTURE.md",
    "THREAT-MODEL.md",
    "SECURITY.md",
    "docs/PRIVACY-ROADMAP.md",
    "docs/SHIELDED-PROTOCOL-MODEL.md",
    "docs/SHIELDED-REVIEW-PLAN.md",
    "docs/PHASE10D-HARDENING.md",
    "docs/PHASE11-NOTE-ENCRYPTION.md",
    "docs/PHASE12B-WALLET-STATE.md",
    "docs/PHASE13A-CORE-VERIFIER-FFI.md",
    "docs/PHASE13B-GENERATED-CORE-HOOK.md",
    "docs/PHASE13C-ATOMIC-STATE.md",
    "docs/PHASE13D-RESOURCE-DOS.md",
    "docs/PHASE14A-RELEASE-IDENTITY.md",
    "docs/PHASE14B-FUZZING.md",
    "docs/PHASE14C-PERFORMANCE.md",
    "docs/PHASE14D-FINAL-HARDENING.md",
    "qualification/PHASE14-STATUS.md",
    "qualification/PHASE15-STATUS.md",
    "reviews/PHASE15C-STATE-MACHINE-REVIEW.md",
    "reviews/PHASE15D-CRYPTO-CIRCUIT-REVIEW.md",
    "reviews/FINDINGS-LEDGER.md",
    "prototypes/zk_balance_halo2/Cargo.lock",
    "prototypes/zk_balance_halo2/Cargo.toml",
    "prototypes/zk_balance_halo2/rust-toolchain.toml",
    "prototypes/zk_balance_halo2/src/context.rs",
    "prototypes/zk_balance_halo2/src/hardened_bundle.rs",
    "prototypes/zk_balance_halo2/src/serialization_v2.rs",
    "prototypes/zk_balance_halo2/src/note_encryption.rs",
    "prototypes/zk_balance_halo2/src/ffi.rs",
    "prototypes/zk_balance_halo2/src/core_state.rs",
    "prototypes/zk_balance_halo2/src/wallet_state.rs",
    "integration/core/phase13b/privacy_verifier.h",
    "integration/core/phase13b/privacy_verifier.cpp",
    "integration/core/phase13b/apply_generated_core.py",
    "integration/core/phase13d/concurrency_smoke.cpp",
]

ALLOWED_AFTER_BASELINE = (
    ".github/workflows/phase15",
    "docs/PHASE15",
    "qualification/PHASE15",
    "qualification/PHASE14-STATUS.md",
    "README.md",
    "scripts/build_phase15_review_package.py",
    "scripts/run_phase15",
    "reviews/",
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    head = git(root, "rev-parse", "HEAD")
    git(root, "cat-file", "-e", f"{BASELINE}^{{commit}}")

    changed = [p for p in git(root, "diff", "--name-only", f"{BASELINE}..HEAD").splitlines() if p]
    forbidden = [
        p for p in changed
        if not any(p == prefix or p.startswith(prefix) for prefix in ALLOWED_AFTER_BASELINE)
    ]
    if forbidden:
        print("PHASE15A_BASELINE_INVALIDATED", file=sys.stderr)
        for p in forbidden:
            print(p, file=sys.stderr)
        return 2

    missing = [p for p in REQUIRED if not (root / p).is_file()]
    if missing:
        print("PHASE15A_REQUIRED_FILE_MISSING", file=sys.stderr)
        for p in missing:
            print(p, file=sys.stderr)
        return 2

    phase14 = (root / "qualification/PHASE14-STATUS.md").read_text(encoding="utf-8")
    if "14D — upgrade/migration/static-review + final evidence ledger | **PASS" not in phase14:
        print("PHASE14D_NOT_CLOSED", file=sys.stderr)
        return 2

    phase15 = (root / "qualification/PHASE15-STATUS.md").read_text(encoding="utf-8")
    for marker in ("PENDING EXTERNAL", "Activation remains a separate WAM maintainer/governance decision"):
        if marker not in phase15:
            print(f"PHASE15_BOUNDARY_MISSING: {marker}", file=sys.stderr)
            return 2

    files = {
        p: {"sha256": sha256(root / p), "bytes": (root / p).stat().st_size}
        for p in REQUIRED
    }

    report = {
        "schema": 1,
        "stage": "phase-15a-review-handoff-freeze",
        "qualification_baseline_commit": BASELINE,
        "prior_superseded_baseline": "00f8065c4f7b48fec01e4d97626ecbf2cc125852",
        "package_commit": head,
        "phase14d": {
            "workflow_run": 37713224314,
            "artifact_digest": "sha256:4d40d3292e46777ee6f211b53b84e93c168dd17a2b4fbae72a1bbe64cea4e64e",
            "status": "PASS_INTERNAL_ENGINEERING",
        },
        "external_review": {
            "state_machine": "PENDING_EXTERNAL",
            "cryptographic_circuit": "PENDING_EXTERNAL",
        },
        "extended_testnet": "PENDING_OPERATOR_EVIDENCE",
        "v1_public_release": "BLOCKED_PENDING_INDEPENDENT_REVIEW",
        "maintainer_activation": "OUT_OF_SCOPE_FOR_AUTOMATIC_PASS",
        "changed_after_baseline": changed,
        "files": files,
        "result": "PASS_REVIEW_PACKAGE_READY",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
