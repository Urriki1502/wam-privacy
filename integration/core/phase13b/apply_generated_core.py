#!/usr/bin/env python3
"""Apply Phase 13B to an already generated/patched WAM Core tree.

This is intentionally an integration harness, not a silent Core fork.
It only changes the ephemeral generated tree used by qualification CI.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


MARKER_INCLUDE = "// WAM-PRIVACY-P13B: experimental verifier include"
MARKER_RPC = "// WAM-PRIVACY-P13B: experimental verifier RPC"
MARKER_COMMAND = "// WAM-PRIVACY-P13B: register experimental verifier RPC"
MARKER_CLIENT_CONVERT = "// WAM-PRIVACY-P13B: verifier RPC numeric conversion"
MARKER_CPPFLAGS = "# WAM-PRIVACY-P13B: verifier compile gate"
MARKER_LDADD = "# WAM-PRIVACY-P13B: verifier link gate"


def die(message: str) -> None:
    raise SystemExit(message)


def replace_once(text: str, needle: str, replacement: str, label: str) -> str:
    count = text.count(needle)
    if count != 1:
        die(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(needle, replacement, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, type=Path)
    ap.add_argument("--privacy-repo", required=True, type=Path)
    args = ap.parse_args()

    tree = args.tree.resolve()
    privacy_repo = args.privacy_repo.resolve()

    rpc = tree / "src/wam/rpc/wam_rpc.cpp"
    rpc_client = tree / "src/rpc/client.cpp"
    makefile = tree / "src/Makefile.am"
    target_dir = tree / "src/wam/privacy"
    integration_dir = privacy_repo / "integration/core/phase13b"
    ffi_header = (
        privacy_repo
        / "prototypes/zk_balance_halo2/include/wam_privacy_halo2.h"
    )

    for required in (rpc, rpc_client, makefile, ffi_header, integration_dir / "privacy_verifier.h",
                     integration_dir / "privacy_verifier.cpp"):
        if not required.exists():
            die(f"missing required path: {required}")

    rpc_text = rpc.read_text(encoding="utf-8")
    if MARKER_INCLUDE not in rpc_text:
        include_anchor = "#include <wam/crypto/randomx_hash.h>\n"
        rpc_text = replace_once(
            rpc_text,
            include_anchor,
            include_anchor
            + f"\n{MARKER_INCLUDE}\n"
            + "#ifdef ENABLE_WAM_PRIVACY_EXPERIMENTAL\n"
            + "#include <wam/privacy/privacy_verifier.h>\n"
            + "#endif\n",
            "rpc include",
        )

    if MARKER_RPC not in rpc_text:
        function_anchor = (
            "// ===========================================================================\n\n"
            "void RegisterWamRPCCommands(CRPCTable& t)\n"
        )
        function = r'''
// WAM-PRIVACY-P13B: experimental verifier RPC
#ifdef ENABLE_WAM_PRIVACY_EXPERIMENTAL
static RPCHelpMan verifyshieldedproof()
{
    return RPCHelpMan{
        "verifyshieldedproof",
        "\nEXPERIMENTAL / REGTEST ONLY. Verify one Phase 10D shielded proof envelope.\n"
        "This RPC is read-only and does not mutate chain or wallet state.\n",
        {
            {"envelope", RPCArg::Type::STR_HEX, RPCArg::Optional::NO,
             "canonical hardened proof envelope as hex"},
            {"transaction_digest", RPCArg::Type::STR_HEX, RPCArg::Optional::NO,
             "32-byte transaction context digest as hex"},
            {"transparent_in", RPCArg::Type::NUM, RPCArg::Optional::NO,
             "transparent input atoms"},
            {"transparent_out", RPCArg::Type::NUM, RPCArg::Optional::NO,
             "transparent output atoms"},
            {"fee", RPCArg::Type::NUM, RPCArg::Optional::NO,
             "fee atoms"},
        },
        RPCResult{RPCResult::Type::OBJ, "", "", {
            {RPCResult::Type::BOOL, "valid", "true only when the proof verifies"},
            {RPCResult::Type::NUM, "status", "stable verifier status code"},
        }},
        RPCExamples{HelpExampleCli(
            "verifyshieldedproof",
            "\"<envelopehex>\" \"<txdigest>\" 10000 2000 3000")},
        [&](const RPCHelpMan& self, const JSONRPCRequest& request) -> UniValue
        {
            if (Params().GetChainType() != ChainType::REGTEST) {
                throw JSONRPCError(
                    RPC_INVALID_PARAMETER,
                    "verifyshieldedproof is experimental and regtest-only");
            }

            const std::string envelope_hex = request.params[0].get_str();
            constexpr size_t MAX_ENVELOPE_BYTES = (4U * 1024U * 1024U) + 1024U;
            if (envelope_hex.size() > MAX_ENVELOPE_BYTES * 2U || !IsHex(envelope_hex)) {
                throw JSONRPCError(RPC_INVALID_PARAMETER, "invalid proof envelope hex");
            }

            const std::string tx_digest_hex = request.params[1].get_str();
            if (tx_digest_hex.size() != 64U || !IsHex(tx_digest_hex)) {
                throw JSONRPCError(
                    RPC_INVALID_PARAMETER,
                    "transaction_digest must be exactly 32 bytes of hex");
            }

            const int64_t transparent_in = request.params[2].getInt<int64_t>();
            const int64_t transparent_out = request.params[3].getInt<int64_t>();
            const int64_t fee = request.params[4].getInt<int64_t>();
            if (transparent_in < 0 || transparent_out < 0 || fee < 0) {
                throw JSONRPCError(
                    RPC_INVALID_PARAMETER,
                    "transparent values and fee must be non-negative");
            }

            const auto digest_bytes = ParseHex(tx_digest_hex);
            wam::privacy::VerifyRequest verify_request;
            verify_request.envelope = ParseHex(envelope_hex);
            std::copy(
                digest_bytes.begin(),
                digest_bytes.end(),
                verify_request.transaction_digest.begin());
            verify_request.transparent_in = static_cast<uint64_t>(transparent_in);
            verify_request.transparent_out = static_cast<uint64_t>(transparent_out);
            verify_request.fee = static_cast<uint64_t>(fee);

            const auto status = wam::privacy::VerifyRegtest(verify_request);
            UniValue out(UniValue::VOBJ);
            out.pushKV("valid", status == wam::privacy::VerifyStatus::OK);
            out.pushKV("status", static_cast<int32_t>(status));
            return out;
        }};
}
#endif
'''
        rpc_text = replace_once(
            rpc_text,
            function_anchor,
            function
            + "\n// ===========================================================================\n\n"
            + "void RegisterWamRPCCommands(CRPCTable& t)\n",
            "rpc function",
        )

    if MARKER_COMMAND not in rpc_text:
        command_anchor = '        {"wam", &getemissionschedule},\n'
        rpc_text = replace_once(
            rpc_text,
            command_anchor,
            command_anchor
            + f"#ifdef ENABLE_WAM_PRIVACY_EXPERIMENTAL\n"
            + f"        {MARKER_COMMAND}\n"
            + '        {"wam-experimental", &verifyshieldedproof},\n'
            + "#endif\n",
            "rpc command",
        )

    client_text = rpc_client.read_text(encoding="utf-8")
    if MARKER_CLIENT_CONVERT not in client_text:
        convert_anchor = "static const CRPCConvertParam vRPCConvertParams[] =\n{\n"
        client_text = replace_once(
            client_text,
            convert_anchor,
            convert_anchor
            + f"    {MARKER_CLIENT_CONVERT}\n"
            + '    { "verifyshieldedproof", 2, "transparent_in" },\n'
            + '    { "verifyshieldedproof", 3, "transparent_out" },\n'
            + '    { "verifyshieldedproof", 4, "fee" },\n',
            "RPC client conversion",
        )

    make_text = makefile.read_text(encoding="utf-8")
    verifier_source = "  wam/privacy/privacy_verifier.cpp \\\n"
    if verifier_source not in make_text:
        source_anchor = "  wam/rpc/wam_rpc.cpp \\\n"
        make_text = replace_once(
            make_text,
            source_anchor,
            source_anchor + verifier_source,
            "Makefile source",
        )

    if MARKER_CPPFLAGS not in make_text:
        cppflags_anchor = "libbitcoin_node_a_CPPFLAGS = "
        if make_text.count(cppflags_anchor) != 1:
            die(
                "Makefile cppflags: expected exactly one "
                "libbitcoin_node_a_CPPFLAGS assignment"
            )
        line_end = make_text.index("\n", make_text.index(cppflags_anchor)) + 1
        make_text = (
            make_text[:line_end]
            + f"{MARKER_CPPFLAGS}\n"
            + "libbitcoin_node_a_CPPFLAGS += $(WAM_PRIVACY_CPPFLAGS)\n"
            + make_text[line_end:]
        )

    if MARKER_LDADD not in make_text:
        ldadd_anchor = "wamd_LDADD = $(LIBBITCOIN_NODE) $(bitcoin_bin_ldadd)\n"
        make_text = replace_once(
            make_text,
            ldadd_anchor,
            ldadd_anchor
            + f"{MARKER_LDADD}\n"
            + "wamd_LDADD += $(WAM_PRIVACY_LIB)\n",
            "Makefile wamd linker",
        )

    # Commit the generated-tree mutation only after every anchor has been
    # validated. An anchor failure must leave the generated Core tree unchanged.
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(integration_dir / "privacy_verifier.h", target_dir / "privacy_verifier.h")
    shutil.copy2(integration_dir / "privacy_verifier.cpp", target_dir / "privacy_verifier.cpp")
    shutil.copy2(ffi_header, target_dir / "wam_privacy_halo2.h")
    rpc.write_text(rpc_text, encoding="utf-8")
    rpc_client.write_text(client_text, encoding="utf-8")
    makefile.write_text(make_text, encoding="utf-8")

    print("PHASE13B_PATCH_APPLIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
