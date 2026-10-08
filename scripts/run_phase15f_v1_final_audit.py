#!/usr/bin/env python3
"""Final internal V1 audit gate for the frozen WAM Privacy candidate.

This gate is intentionally conservative. It does not claim an independent audit,
production readiness, mainnet readiness, or consensus activation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASELINE = "15fafa199871f7a1688b1beda5e27005ae473d27"

ACTIVE_RUNTIME_FILES = [
    "prototypes/zk_balance_halo2/src/lib.rs",
    "prototypes/zk_balance_halo2/src/context.rs",
    "prototypes/zk_balance_halo2/src/hardened_bundle.rs",
    "prototypes/zk_balance_halo2/src/serialization_v2.rs",
    "prototypes/zk_balance_halo2/src/note_encryption.rs",
    "prototypes/zk_balance_halo2/src/wallet_state.rs",
    "prototypes/zk_balance_halo2/src/core_state.rs",
    "prototypes/zk_balance_halo2/src/ffi.rs",
    "integration/core/phase13b/privacy_verifier.h",
    "integration/core/phase13b/privacy_verifier.cpp",
    "integration/core/phase13b/apply_generated_core.py",
]

ALLOWED_AFTER_BASELINE = (
    ".github/workflows/phase15",
    "docs/PHASE15",
    "qualification/PHASE15",
    "qualification/PHASE14-STATUS.md",
    "reviews/",
    "README.md",
    "scripts/build_phase15_review_package.py",
    "scripts/run_phase15",
    "scripts/run_phase15f",
    "scripts/build_phase15f",
    # Exact freeze qualification metadata only. No protected source prefix.
    ".github/workflows/v1-logical-freeze-clean-clone.yml",
    "qualification/v1-freeze/candidate.json",
    "scripts/qualify_v1_logical_freeze.py",
    ".github/workflows/v2-01-capability-policy.yml",
    "docs/v2/",   # Isolated V2 docs; protected V1 source remains immutable.
    "v2/",        # Isolated V2 policy/tests; not a Core or V1 runtime path.
)

FORBIDDEN_PLACEHOLDERS = (
    "todo!(",
    "unimplemented!(",
    "dbg!(",
    "TODO_SECURITY",
    "FIXME_SECURITY",
)

PANIC_ALLOWLIST = {
    "prototypes/zk_balance_halo2/src/hardened_bundle.rs": [
        'expect("range starts at row zero")',
    ],
    "prototypes/zk_balance_halo2/src/core_state.rs": [
        'expect("checked non-empty history")',
    ],
    "prototypes/zk_balance_halo2/src/wallet_state.rs": [
        'expect("tree has root level")',
        'expect("recognized note is canonical")',
    ],
    "prototypes/zk_balance_halo2/src/lib.rs": [
        'expect("range accumulator exists")',
    ],
}

REQUIRED_TOKENS = {
    "prototypes/zk_balance_halo2/src/lib.rs": [
        "pub const MAX_WAM_ATOMS: u64 = 22_000_000 * 100_000_000;",
    ],
    "prototypes/zk_balance_halo2/src/context.rs": [
        'b"WAM/Privacy/ProofContext/v1"',
        "CIRCUIT_ID_HARDENED_2X2",
        "transaction_digest",
        "transparent_in",
        "transparent_out",
        "fee",
    ],
    "prototypes/zk_balance_halo2/src/serialization_v2.rs": [
        "checked_add",
        "VkIdMismatch",
        "ContextMismatch",
        "TransparentBalanceMismatch",
        "verify_proof",
        "TrailingBytes",
        "NonCanonicalField",
    ],
    "prototypes/zk_balance_halo2/src/note_encryption.rs": [
        "Zeroizing",
        "X25519HkdfSha256",
        "HkdfSha256",
        "ChaCha20Poly1305",
        'b"WAM/Shielded/NoteHPKE/v1"',
        "AddressMismatch",
        "TrailingBytes",
    ],
    "prototypes/zk_balance_halo2/src/wallet_state.rs": [
        "let mut candidate = self.clone();",
        "candidate.apply_block(block)?;",
        "NetworkMismatch",
        "DuplicateCommitment",
        "TreeFull",
    ],
    "prototypes/zk_balance_halo2/src/core_state.rs": [
        "let mut candidate = self.clone();",
        "checked_add",
        "checked_sub",
        "MAX_TRANSITIONS_PER_BLOCK",
        "DuplicateNullifier",
        "DuplicateCommitment",
        "disconnect_tip",
    ],
    "prototypes/zk_balance_halo2/src/ffi.rs": [
        "catch_unwind",
        "NetworkId::Regtest",
        "MAX_PROOF_BYTES",
        "MAX_WAM_ATOMS",
        "ptr::null_mut()",
    ],
    "integration/core/phase13b/privacy_verifier.cpp": [
        "ENABLE_WAM_PRIVACY_EXPERIMENTAL",
        "VerifyRegtest",
        "std::try_to_lock",
        "VerifyStatus::BUSY",
    ],
    "integration/core/phase13b/apply_generated_core.py": [
        "ChainType::REGTEST",
        "MAX_ENVELOPE_BYTES",
        "ENABLE_WAM_PRIVACY_EXPERIMENTAL",
        "This RPC is read-only and does not mutate chain or wallet state.",
    ],
}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_token(text: str, token: str) -> int:
    return text.count(token)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    root = args.root.resolve()
    head = git(root, "rev-parse", "HEAD")
    git(root, "cat-file", "-e", f"{BASELINE}^{{commit}}")
    git(root, "merge-base", "--is-ancestor", BASELINE, "HEAD")

    changed = [
        p
        for p in git(root, "diff", "--name-only", f"{BASELINE}..HEAD").splitlines()
        if p
    ]
    frozen_source_changes = [
        p
        for p in changed
        if not any(p == prefix or p.startswith(prefix) for prefix in ALLOWED_AFTER_BASELINE)
    ]

    violations: list[dict[str, object]] = []
    observations: list[dict[str, object]] = []
    files: dict[str, dict[str, object]] = {}

    if frozen_source_changes:
        violations.append({
            "id": "V1-FREEZE-001",
            "severity": "HIGH",
            "message": "Runtime/protocol file changed after the merged P0-remediated V1 source baseline.",
            "paths": frozen_source_changes,
        })

    for rel in ACTIVE_RUNTIME_FILES:
        path = root / rel
        if not path.is_file():
            violations.append({
                "id": "V1-SOURCE-001",
                "severity": "HIGH",
                "message": f"Required active runtime file missing: {rel}",
            })
            continue

        raw = path.read_bytes()
        text = raw.decode("utf-8")
        runtime_text = text.split("\n#[cfg(test)]", 1)[0] if rel.endswith(".rs") else text
        files[rel] = {"sha256": digest(path), "bytes": len(raw)}

        for token in FORBIDDEN_PLACEHOLDERS:
            if token in text:
                violations.append({
                    "id": "V1-PLACEHOLDER-001",
                    "severity": "HIGH",
                    "path": rel,
                    "token": token,
                })

        if rel.endswith(".rs"):
            if "unsafe" in runtime_text and rel != "prototypes/zk_balance_halo2/src/ffi.rs":
                violations.append({
                    "id": "V1-UNSAFE-001",
                    "severity": "HIGH",
                    "path": rel,
                    "message": "Unsafe Rust outside the dedicated FFI module.",
                })

            risky = {
                "unwrap(": count_token(runtime_text, "unwrap("),
                "expect(": count_token(runtime_text, "expect("),
                "panic!(": count_token(runtime_text, "panic!("),
            }
            allowed = PANIC_ALLOWLIST.get(rel, [])
            allowed_expect = sum(runtime_text.count(token) for token in allowed)
            unknown_expect = max(0, risky["expect("] - allowed_expect)
            if risky["unwrap("] or risky["panic!("] or unknown_expect:
                violations.append({
                    "id": "V1-PANIC-001",
                    "severity": "MEDIUM",
                    "path": rel,
                    "counts": risky,
                    "allowlisted_expect": allowed_expect,
                    "message": "Unexpected panic-capable primitive in active runtime path.",
                })
            elif allowed_expect:
                observations.append({
                    "id": "V1-PANIC-AUDITED",
                    "path": rel,
                    "count": allowed_expect,
                    "classification": "deterministic internal invariant; no attacker-controlled branch identified",
                })

    for rel, tokens in REQUIRED_TOKENS.items():
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [token for token in tokens if token not in text]
        if missing:
            violations.append({
                "id": "V1-INVARIANT-001",
                "severity": "HIGH",
                "path": rel,
                "missing_tokens": missing,
            })

    # P0 constraints must be part of the proof relation, not only values set by
    # the honest prover. This is a source/invariant guard, not a ZK soundness proof.
    for rel in (
        "prototypes/zk_balance_halo2/src/hardened_bundle.rs",
        "prototypes/zk_balance_halo2/src/bundle_action.rs",
    ):
        source = (root / rel).read_text(encoding="utf-8")
        for domain in ("NOTE_DOMAIN", "AUTHORITY_DOMAIN", "NULLIFIER_DOMAIN"):
            if f"Value::known(Fp::from({domain}))" in source:
                violations.append({
                    "id": "V1-P0-REINTRODUCED-DOMAIN",
                    "severity": "HIGH",
                    "path": rel,
                    "domain": domain,
                })
        if source.count("assign_advice_from_constant(") < 4:
            violations.append({
                "id": "V1-P0-CONSTANT-BINDING",
                "severity": "HIGH",
                "path": rel,
                "message": "Bundle must bind input/output domain constants in circuit.",
            })

    core_text = (root / "prototypes/zk_balance_halo2/src/core_state.rs").read_text(encoding="utf-8")
    verified_decl = core_text.split("pub struct VerifiedTransition {", 1)
    if len(verified_decl) != 2 or any(
        field in verified_decl[1].split("}", 1)[0]
        for field in (
            "pub anchor:",
            "pub nullifiers:",
            "pub output_commitments:",
            "pub transparent_in:",
            "pub transparent_out:",
            "pub fee:",
        )
    ):
        violations.append({
            "id": "V1-P0-UNTRUSTED-TRANSITION",
            "severity": "HIGH",
            "message": "VerifiedTransition proof-derived fields must be private.",
        })

    note_text = (root / "prototypes/zk_balance_halo2/src/note_encryption.rs").read_text(encoding="utf-8")
    hardened_text = (root / "prototypes/zk_balance_halo2/src/hardened_bundle.rs").read_text(encoding="utf-8")
    if "#[derive(Clone, Debug, PartialEq, Eq)]\npub struct NotePlaintext" in note_text:
        observations.append({
            "id": "V1-SECRET-DEBUG-001",
            "severity": "MEDIUM",
            "classification": "remediation-recommended-before-release",
            "path": "prototypes/zk_balance_halo2/src/note_encryption.rs",
            "message": "NotePlaintext derives Debug; accidental debug logging could disclose note plaintext.",
        })
    if "#[derive(Clone, Debug)]\npub struct HardenedBundleInput" in hardened_text or "#[derive(Clone, Debug)]\npub struct HardenedBundleCircuit" in hardened_text:
        observations.append({
            "id": "V1-SECRET-DEBUG-002",
            "severity": "MEDIUM",
            "classification": "remediation-recommended-before-release",
            "path": "prototypes/zk_balance_halo2/src/hardened_bundle.rs",
            "message": "Private Halo2 witness containers derive Debug; accidental debug logging could disclose witness material.",
        })
    if "let spend_vec = derive_bytes" in note_text or "let incoming_vec = derive_bytes" in note_text or "let audit_vec = derive_bytes" in note_text:
        observations.append({
            "id": "V1-KEY-ZEROIZE-001",
            "severity": "LOW",
            "classification": "remediation-recommended-before-release",
            "path": "prototypes/zk_balance_halo2/src/note_encryption.rs",
            "message": "Intermediate derived-key Vec buffers are not explicitly wrapped in Zeroizing.",
        })

    report = {
        "schema": 1,
        "stage": "phase-15f-v1-final-internal-audit",
        "baseline_commit": BASELINE,
        "audit_head": head,
        "changed_after_baseline": changed,
        "active_runtime_files": files,
        "observations": observations,
        "violations": violations,
        "baseline_type": "post-P0 merged source commit, not a production release",
        "independent_review": "PENDING_EXTERNAL_15C_15D",
        "extended_testnet": "PENDING_OPERATOR_EVIDENCE",
        "public_release": "BLOCKED",
        "residual_nonclaims": [
            "Independent Phase 15C/15D reports are external evidence and are not created by this gate.",
            "Generated WAM Core integration remains experimental and regtest-only.",
            "The research Core state model receives next_anchor from the higher-level tree integration boundary.",
            "No public-testnet or mainnet readiness claim is made.",
        ],
        "result": "PASS_INTERNAL_FINAL_AUDIT" if not violations else "FAIL_INTERNAL_FINAL_AUDIT",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

    if violations:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
