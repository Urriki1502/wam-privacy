#!/usr/bin/env python3
"""Verify the generated-Core Phase 13B patch contract."""

from __future__ import annotations

import argparse
from pathlib import Path


RPC_MARKERS = (
    "WAM-PRIVACY-P13B: experimental verifier include",
    "WAM-PRIVACY-P13B: experimental verifier RPC",
    "WAM-PRIVACY-P13B: register experimental verifier RPC",
)
CLIENT_MARKER = "WAM-PRIVACY-P13B: verifier RPC numeric conversion"
MAKE_MARKERS = (
    "WAM-PRIVACY-P13B: verifier compile gate",
    "WAM-PRIVACY-P13B: verifier link gate",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, type=Path)
    args = ap.parse_args()
    tree = args.tree.resolve()

    rpc = tree / "src/wam/rpc/wam_rpc.cpp"
    rpc_client = tree / "src/rpc/client.cpp"
    makefile = tree / "src/Makefile.am"
    verifier_cpp = tree / "src/wam/privacy/privacy_verifier.cpp"
    verifier_h = tree / "src/wam/privacy/privacy_verifier.h"
    ffi_h = tree / "src/wam/privacy/wam_privacy_halo2.h"

    for path in (rpc, rpc_client, makefile, verifier_cpp, verifier_h, ffi_h):
        require(path.is_file(), f"missing Phase 13B generated path: {path}")

    rpc_text = rpc.read_text(encoding="utf-8")
    client_text = rpc_client.read_text(encoding="utf-8")
    make_text = makefile.read_text(encoding="utf-8")
    verifier_text = verifier_cpp.read_text(encoding="utf-8")

    for marker in RPC_MARKERS:
        require(rpc_text.count(marker) == 1, f"RPC marker count != 1: {marker}")
    require(client_text.count(CLIENT_MARKER) == 1, "RPC client conversion marker count != 1")
    for name, index in (
        ("transparent_in", 2),
        ("transparent_out", 3),
        ("fee", 4),
    ):
        require(
            f'{{ "verifyshieldedproof", {index}, "{name}" }},' in client_text,
            f"RPC client numeric conversion missing: {name}",
        )
    for marker in MAKE_MARKERS:
        require(make_text.count(marker) == 1, f"Makefile marker count != 1: {marker}")
    require(
        make_text.count("  wam/privacy/privacy_verifier.cpp \\") == 1,
        "verifier source count != 1",
    )

    require(
        "Params().GetChainType() != ChainType::REGTEST" in rpc_text,
        "regtest runtime gate missing",
    )
    require(
        "#ifdef ENABLE_WAM_PRIVACY_EXPERIMENTAL" in rpc_text,
        "experimental compile gate missing from RPC",
    )
    require(
        "libbitcoin_node_a_CPPFLAGS += $(WAM_PRIVACY_CPPFLAGS)" in make_text,
        "node-library experimental CPPFLAGS hook missing",
    )
    require(
        "wamd_LDADD += $(WAM_PRIVACY_LIB)" in make_text,
        "wamd verifier-library link hook missing",
    )
    require(
        "static Holder holder;" in verifier_text
        and "static std::mutex verify_mutex;" in verifier_text,
        "long-lived serialized verifier wrapper missing",
    )
    require(
        "wam_privacy_halo2_verify_hardened_v1" in verifier_text,
        "Phase 13A verifier ABI call missing",
    )
    require(
        "std::try_to_lock" in verifier_text and "VerifyStatus::BUSY" in verifier_text,
        "non-blocking verifier concurrency gate missing",
    )

    for relative in ("src/validation.cpp", "src/txmempool.cpp", "src/coins.cpp"):
        path = tree / relative
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            require("WAM-PRIVACY-P13B" not in text, f"13B marker leaked into {relative}")

    print("PHASE13B_GENERATED_CORE_CONTRACT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
