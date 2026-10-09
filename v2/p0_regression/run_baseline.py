"""Offline independent baseline regression and honest evidence manifest."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
V1 = "95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127"
V2 = "5af86cfd5be27a3275079cbccde2abd2366ebb2b"
def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    head = git("rev-parse", "HEAD")
    expected = os.environ["EXPECTED_HEAD"]
    if head != expected:
        raise RuntimeError("exact HEAD mismatch")
    subprocess.run(["git", "diff", "--exit-code", V2, "HEAD", "--",
                    "prototypes/", "integration/", "tests/", "v2/policy.py",
                    "v2/disclosure.py", "v2/routing.py", "v2/bridge.py"], check=True)
    env = dict(os.environ, PYTHONPATH="v2:prototypes", PYTHONDONTWRITEBYTECODE="1")
    modules = ["v2.test_policy", "v2.test_disclosure", "v2.test_routing",
               "v2.test_bridge", "v2.test_qualification",
               "tests.test_phase3_signer_abstraction"]
    subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", *modules],
                   env=env, check=True)
    report = {"schema": 1, "checkout_head": head, "frozen_v1": V1,
              "frozen_v2": V2, "modules_executed": modules,
              "result": "BASELINE_REGRESSION_ONLY",
              "cross_module_atomic_integration": "PENDING_A_B_C",
              "trusted_ui_integration": "PENDING",
              "external_audit": "PENDING_EXTERNAL",
              "CORE-003": "BLOCKED", "production": "BLOCKED",
              "ci_verdict": "VERIFY_ACTIONS_AT_EXACT_HEAD",
              "network_wallet_funds": "NONE"}
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
if __name__ == "__main__":
    main()
