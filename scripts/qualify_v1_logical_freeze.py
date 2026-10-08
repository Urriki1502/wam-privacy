#!/usr/bin/env python3
"""Evidence-only logical-freeze verifier for a pinned WAM Privacy V1 source.

Runs on a GitHub-hosted clean checkout, not on an arbitrary mutable worktree.
Never publishes an on-chain feature, Git tag, release, audit certificate, or
maintainer approval. The generated manifest applies ONLY to the pinned commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


FROZEN_PREFIXES = (
    "prototypes/zk_balance_halo2/",
    "integration/core/",
    "tests/",
    "scripts/phase14d_static_review.py",
    "scripts/build_phase14d_ledger.py",
)


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True
    ).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(message: str) -> None:
    raise SystemExit("V1_FREEZE_VALIDATION_FAILED: " + message)


def parse_identity(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    result = {}
    for line in lines:
        if not line:
            continue
        if line.count("=") != 1:
            fail(f"malformed identity record in {path}")
        key, value = line.split("=", 1)
        if key in result:
            fail("duplicate identity field: " + key)
        result[key] = value
    expected = {"protocol_version", "circuit_id", "verifier_k", "vk_id"}
    if set(result) != expected:
        fail("identity field mismatch " + str(sorted(set(result) ^ expected)))
    return result


def preflight(
    qualification: Path,
    first: Path,
    second: Path,
    candidate: dict,
) -> dict:
    pin = candidate["candidate_source_commit"]
    p0 = candidate["p0_remediated_source_baseline"]
    if not all(len(c) == 40 and set(c) <= set("0123456789abcdef") for c in (pin, p0)):
        fail("invalid pinned source SHA")
    if first.resolve() == second.resolve():
        fail("clean clone directories must be distinct")
    if first.resolve() == qualification.resolve() or second.resolve() == qualification.resolve():
        fail("qualification checkout cannot substitute a clean clone")
    for clone in (first, second):
        if git(clone, "rev-parse", "HEAD") != pin:
            fail(f"clean checkout HEAD does not match pinned V1 source: {clone}")
        if git(clone, "status", "--porcelain"):
            fail(f"clean checkout has a dirty worktree: {clone}")
    if git(first, "rev-parse", "HEAD^{tree}") != git(second, "rev-parse", "HEAD^{tree}"):
        fail("independent checkouts have different source trees")
    subprocess.run(
        ["git", "-C", str(qualification), "merge-base", "--is-ancestor", pin, "HEAD"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(qualification), "merge-base", "--is-ancestor", p0, pin],
        check=True,
    )
    changes = [
        entry for entry in git(qualification, "diff", "--name-only", pin + "..HEAD").splitlines()
        if entry
    ]
    forbidden = [
        entry for entry in changes
        if any(entry == prefix or entry.startswith(prefix) for prefix in FROZEN_PREFIXES)
    ]
    if forbidden:
        fail("protected V1 implementation/test code changed after pin: " + ", ".join(forbidden))
    # Reject edits to the pinned core WAM privacy protocol inputs, independently
    # of whether a later qualification document labels them as non-runtime.
    manifest = candidate["proof_profile"]
    if manifest["protocol_version"] != 1 or manifest["circuit_id"] != 2564:
        fail("unexpected protocol or circuit version")
    if manifest["verifier_k"] != 15:
        fail("unexpected Halo2 verifier k")
    if manifest["supply_cap_atoms"] != "2200000000000000":
        fail("supply cap drift")
    if candidate["toolchain"] != "1.88.0":
        fail("rust toolchain drift")
    if candidate["status"]["public_release"] != "BLOCKED_INDEPENDENT_REVIEW_AND_OPERATOR_TESTNET":
        fail("release gate was silently lifted")
    if candidate["status"]["independent_state_machine_review"] != "PENDING_15C":
        fail("missing independent state-machine audit boundary")
    if candidate["status"]["independent_cryptographic_review"] != "PENDING_15D":
        fail("missing independent cryptographic audit boundary")
    if candidate["status"]["github_tag"] != "TAG_RELEASE_PENDING":
        fail("unexpected V1 tag claim")
    return {
        "candidate_source_commit": pin,
        "p0_source_baseline": p0,
        "source_tree": git(first, "rev-parse", "HEAD^{tree}"),
        "qualification_head": git(qualification, "rev-parse", "HEAD"),
        "v1_source_changes_after_pin": forbidden,
        "post_pin_metadata_paths": changes,
        "preflight": "PASS",
    }


def finish(
    first: Path,
    second: Path,
    candidate: dict,
    evidence: dict,
    output: Path,
    identity_a: Path,
    identity_b: Path,
    library_a: Path,
    library_b: Path,
) -> None:
    a, b = parse_identity(identity_a), parse_identity(identity_b)
    if a != b:
        fail("separate clean checkouts produced different circuit/VK identities")
    profile = candidate["proof_profile"]
    expected = {
        "protocol_version": str(profile["protocol_version"]),
        "circuit_id": str(profile["circuit_id"]),
        "verifier_k": str(profile["verifier_k"]),
        "vk_id": profile["expected_vk_id"],
    }
    if a != expected:
        fail("identity is not the expected requalified post-P0 VK: " + str(a))
    if not library_a.is_dir() or not library_b.is_dir():
        fail("release build target directory missing")
    binaries = {}
    output.mkdir(parents=True, exist_ok=True)
    target = output / "research-only-binaries"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("libwam_privacy_halo2_prototype.so", "libwam_privacy_halo2_prototype.a"):
        artifact_a = library_a / name
        artifact_b = library_b / name
        if not artifact_a.is_file() or not artifact_b.is_file():
            fail("missing compiled research verifier artifact: " + name)
        digest_a, digest_b = sha(artifact_a), sha(artifact_b)
        if digest_a != digest_b:
            fail("independent clean builds do not have identical SHA-256: " + name)
        shutil.copy2(artifact_a, target / name)
        binaries[name] = {"sha256": digest_a, "bytes": artifact_a.stat().st_size}

    paths = [
        "prototypes/zk_balance_halo2/Cargo.toml",
        "prototypes/zk_balance_halo2/Cargo.lock",
        "prototypes/zk_balance_halo2/rust-toolchain.toml",
        "prototypes/zk_balance_halo2/examples/release_identity.rs",
        "qualification/manifest.json",
    ]
    provenance = {
        p: {"sha256": sha(first / p), "bytes": (first / p).stat().st_size}
        for p in paths
    }
    source_archive = output / "v1-frozen-source.tar"
    with source_archive.open("wb") as dest:
        subprocess.run(["git", "-C", str(first), "archive", "--format=tar", "HEAD"],
                       stdout=dest, check=True)

    report = {
        "schema": 1,
        "stage": "v1-logical-freeze-internal-qualification",
        "result": "PASS_INTERNAL_FREEZE_QUALIFICATION",
        "logical_freeze_status": "CANDIDATE_VALIDATED_PENDING_EXPLICIT_FREEZE_RECORD",
        **evidence,
        "independent_clean_git_checkouts": 2,
        "toolchain_expected": candidate["toolchain"],
        "toolchain_observed": subprocess.check_output(
            ["rustc", "--version"], text=True
        ).strip(),
        "proof_profile": profile,
        "verified_release_identity": a,
        "artifact_hashes": binaries,
        "locked_input_hashes": provenance,
        "source_archive": {
            "sha256": sha(source_archive),
            "bytes": source_archive.stat().st_size,
            "format": "git archive --format=tar from immutable pin",
        },
        "upstream_core_pin": candidate["upstream_core"],
        "wsp_pin": candidate["wsp"],
        "status": candidate["status"],
        "non_claims": candidate["non_claims"],
        "external_review": "NOT_PERFORMED",
        "operator_testnet_history": "NOT_PERFORMED",
        "maintainer_activation": "NOT_AUTHORIZED",
    }
    if not report["toolchain_observed"].startswith("rustc 1.88.0 "):
        fail("observed rustc version differs from 1.88.0")
    target_manifest = output / "v1-freeze-qualification.json"
    target_manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    (output / "v1-freeze-qualification.json.sha256").write_text(
        sha(target_manifest) + "  v1-freeze-qualification.json\n", encoding="utf-8"
    )
    print(json.dumps({
        "result": report["result"],
        "source": evidence["candidate_source_commit"],
        "vk_id": a["vk_id"],
        "sharedlib_sha256": binaries["libwam_privacy_halo2_prototype.so"]["sha256"],
        "staticlib_sha256": binaries["libwam_privacy_halo2_prototype.a"]["sha256"],
        "source_archive_sha256": report["source_archive"]["sha256"],
        "release": "BLOCKED_PRESERVE_REVIEW_GATES",
    }, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qualification", type=Path, required=True)
    ap.add_argument("--source-a", type=Path, required=True)
    ap.add_argument("--source-b", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--identity-a", type=Path)
    ap.add_argument("--identity-b", type=Path)
    ap.add_argument("--library-a", type=Path)
    ap.add_argument("--library-b", type=Path)
    ap.add_argument("--mode", choices=("preflight", "finalize"), required=True)
    args = ap.parse_args()
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    data = preflight(args.qualification, args.source_a, args.source_b, candidate)
    if args.mode == "finalize":
        if any(x is None for x in (args.output, args.identity_a, args.identity_b, args.library_a, args.library_b)):
            fail("missing finalize arguments")
        finish(args.source_a, args.source_b, candidate, data,
               args.output, args.identity_a, args.identity_b,
               args.library_a, args.library_b)
    else:
        print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        fail("git/build prerequisite failed: " + str(exc))
