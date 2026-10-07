#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REVIEWED = [
    "prototypes/zk_balance_halo2/src/ffi.rs",
    "prototypes/zk_balance_halo2/src/serialization_v2.rs",
    "prototypes/zk_balance_halo2/src/context.rs",
    "prototypes/zk_balance_halo2/src/core_state.rs",
    "prototypes/zk_balance_halo2/src/wallet_state.rs",
    "prototypes/zk_balance_halo2/src/note_encryption.rs",
    "integration/core/phase13b/privacy_verifier.cpp",
    "integration/core/phase13b/privacy_verifier.h",
]

FORBIDDEN = ("todo!(", "unimplemented!(", "dbg!(", "TODO_SECURITY", "FIXME_SECURITY")

required_tokens = {
    "prototypes/zk_balance_halo2/src/ffi.rs": [
        "catch_unwind",
        "UnsupportedNetwork",
        "ptr::write(out, ptr::null_mut())",
    ],
    "integration/core/phase13b/privacy_verifier.cpp": [
        "std::try_to_lock",
        "VerifyStatus::BUSY",
        "ENABLE_WAM_PRIVACY_EXPERIMENTAL",
    ],
}

records = []
unsafe_files = []
violations = []

for rel in REVIEWED:
    path = ROOT / rel
    if not path.is_file():
        violations.append(f"missing reviewed file: {rel}")
        continue
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    unsafe_count = text.count("unsafe")
    if unsafe_count:
        unsafe_files.append({"path": rel, "unsafe_token_count": unsafe_count})
        if rel != "prototypes/zk_balance_halo2/src/ffi.rs":
            violations.append(f"unsafe token outside FFI boundary: {rel}")
    for marker in FORBIDDEN:
        if marker in text:
            violations.append(f"forbidden marker {marker!r} in {rel}")
    for token in required_tokens.get(rel, []):
        if token not in text:
            violations.append(f"required fail-closed token missing in {rel}: {token}")
    records.append({
        "path": rel,
        "sha256": digest,
        "bytes": len(raw),
        "unsafe_token_count": unsafe_count,
    })

report = {
    "schema": 1,
    "review_scope": "production-facing research boundary",
    "files": records,
    "unsafe_inventory": unsafe_files,
    "forbidden_markers": list(FORBIDDEN),
    "violations": violations,
    "result": "PASS" if not violations else "FAIL",
    "claim_boundary": (
        "Machine-checkable static boundary inventory only; not an independent "
        "manual security audit or formal verification."
    ),
}

out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reports/phase14d/static-review.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
raise SystemExit(0 if not violations else 2)
