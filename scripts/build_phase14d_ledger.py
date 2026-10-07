#!/usr/bin/env python3
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

files = [
    "prototypes/zk_balance_halo2/Cargo.lock",
    "prototypes/zk_balance_halo2/Cargo.toml",
    "prototypes/zk_balance_halo2/rust-toolchain.toml",
    "prototypes/zk_balance_halo2/src/context.rs",
    "prototypes/zk_balance_halo2/src/serialization_v2.rs",
    "prototypes/zk_balance_halo2/src/hardened_bundle.rs",
    "prototypes/zk_balance_halo2/src/ffi.rs",
    "qualification/phase14a-release-identity.json",
]

hashes = {}
for rel in files:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"missing ledger input: {rel}")
    hashes[rel] = sha256(path)

static_review = ROOT / "reports/phase14d/static-review.json"
if not static_review.is_file():
    raise SystemExit("static review evidence missing")

ledger = {
    "schema": 1,
    "phase": "14D",
    "source_head": git("rev-parse", "HEAD"),
    "source_tree": git("rev-parse", "HEAD^{tree}"),
    "phase14_evidence": {
        "14A": {
            "run": 37610249058,
            "artifact_digest": "sha256:6f03aff679d3e9a104b8e9bc0c6570436eaafd288bdc5f5fdae4a6369d09cf49",
        },
        "14B": {
            "run": 37615083459,
            "qualification_head": "9798d4aa4d1367f91ce3eaea7d30d14d8133a76c",
        },
        "14C": {
            "run": 37620295551,
            "artifact_digest": "sha256:37ed1953b9e7fd120cc287311d245408ad309fb76586e2c95fe6a242dbe54595",
            "observed": {
                "setup_ms": 50637,
                "prove_ms": 17369,
                "verify_avg_ms": 305,
                "verify_max_ms": 306,
                "proof_bytes": 5728,
                "envelope_bytes": 6061,
                "peak_rss_kb": 1498028,
            },
        },
    },
    "bound_file_sha256": hashes,
    "static_review_sha256": sha256(static_review),
    "claim_boundary": (
        "Internal engineering hardening ledger. External cryptographic review, "
        "extended testnet evidence and activation decisions are Phase 15."
    ),
}

out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reports/phase14d/final-ledger.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(ledger, indent=2) + "\n")
print(json.dumps(ledger, indent=2))
