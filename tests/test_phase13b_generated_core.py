import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PATCHER = REPO / "integration/core/phase13b/apply_generated_core.py"


def make_tree(root: Path, *, include_ldadd: bool = True) -> Path:
    tree = root / "core"
    rpc = tree / "src/wam/rpc/wam_rpc.cpp"
    makefile = tree / "src/Makefile.am"
    rpc.parent.mkdir(parents=True)
    rpc.write_text(
        "#include <wam/crypto/randomx_hash.h>\n"
        "\n"
        "// ===========================================================================\n\n"
        "void RegisterWamRPCCommands(CRPCTable& t)\n"
        "{\n"
        "    static const CRPCCommand commands[]{\n"
        "        {\"wam\", &getemissionschedule},\n"
        "    };\n"
        "}\n",
        encoding="utf-8",
    )
    make = (
        "libbitcoin_node_a_CPPFLAGS = $(AM_CPPFLAGS) $(BITCOIN_INCLUDES)\n"
        "libbitcoin_node_a_SOURCES = \\\n"
        "  wam/rpc/wam_rpc.cpp \\\n"
        "  validation.cpp\n"
    )
    if include_ldadd:
        make += "wamd_LDADD = $(LIBBITCOIN_NODE) $(bitcoin_bin_ldadd)\n"
    makefile.write_text(make, encoding="utf-8")
    return tree


def apply(tree: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PATCHER),
            "--tree",
            str(tree),
            "--privacy-repo",
            str(REPO),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class Phase13BGeneratedCoreTests(unittest.TestCase):
    def test_patch_is_idempotent_and_explicitly_gated(self):
        with tempfile.TemporaryDirectory() as td:
            tree = make_tree(Path(td))
            first = apply(tree)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = apply(tree)
            self.assertEqual(second.returncode, 0, second.stderr)

            rpc = (tree / "src/wam/rpc/wam_rpc.cpp").read_text(encoding="utf-8")
            make = (tree / "src/Makefile.am").read_text(encoding="utf-8")

            self.assertEqual(rpc.count("WAM-PRIVACY-P13B: experimental verifier include"), 1)
            self.assertEqual(rpc.count("WAM-PRIVACY-P13B: experimental verifier RPC"), 1)
            self.assertEqual(rpc.count("WAM-PRIVACY-P13B: register experimental verifier RPC"), 1)
            self.assertIn("#ifdef ENABLE_WAM_PRIVACY_EXPERIMENTAL", rpc)
            self.assertIn("Params().GetChainType() != ChainType::REGTEST", rpc)
            self.assertIn("This RPC is read-only and does not mutate chain or wallet state.", rpc)

            self.assertEqual(make.count("  wam/privacy/privacy_verifier.cpp \\"), 1)
            self.assertEqual(make.count("WAM-PRIVACY-P13B: verifier compile gate"), 1)
            self.assertEqual(make.count("WAM-PRIVACY-P13B: verifier link gate"), 1)
            self.assertIn(
                "libbitcoin_node_a_CPPFLAGS += $(WAM_PRIVACY_CPPFLAGS)", make
            )
            self.assertIn("wamd_LDADD += $(WAM_PRIVACY_LIB)", make)

            copied = tree / "src/wam/privacy"
            self.assertTrue((copied / "privacy_verifier.h").is_file())
            self.assertTrue((copied / "privacy_verifier.cpp").is_file())
            self.assertTrue((copied / "wam_privacy_halo2.h").is_file())

    def test_anchor_failure_does_not_partially_mutate_tree(self):
        with tempfile.TemporaryDirectory() as td:
            tree = make_tree(Path(td), include_ldadd=False)
            rpc = tree / "src/wam/rpc/wam_rpc.cpp"
            makefile = tree / "src/Makefile.am"
            rpc_before = rpc.read_bytes()
            make_before = makefile.read_bytes()

            result = apply(tree)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Makefile wamd linker", result.stderr + result.stdout)
            self.assertEqual(rpc.read_bytes(), rpc_before)
            self.assertEqual(makefile.read_bytes(), make_before)
            self.assertFalse((tree / "src/wam/privacy").exists())


if __name__ == "__main__":
    unittest.main()
