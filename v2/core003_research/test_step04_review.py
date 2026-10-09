"""CORE-003 Step 04 proposal lint ONLY; never a Core acceptance gate or audit."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "v2/core003_research/step04_contract.json"
DESIGN_PATH = ROOT / "docs/v2/CORE003-STEP04-CORE-INTERFACE-REVIEW.md"

INV_IDS = {f"C4-INV-{i:02d}" for i in range(1, 13)}
DEC_IDS = {f"D{i:02d}" for i in range(1, 11)}
PINNED = {
    "v1": "95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127",
    "v2": "5af86cfd5be27a3275079cbccde2abd2366ebb2b",
    "step01": "1b2718a8e1ab6852949665dbb07af8ac75d2480a",
    "step02": "55158e872b758febc3ca5135d2f47e13744cd386",
    "step03": "ff604db70f5a635e406bd0a8ffd7cdfa05341a0e",
    "wam_core": "260bc468e5adffea7ce68d8f97fac3e27e4c50b2",
    "wsp": "dcf1aecc00a64bfad3151fa202c3e07d47d83e69",
}

def check(data: dict) -> None:
    if type(data) is not dict or data.get("schema_version") != 1:
        raise ValueError("schema")
    if data.get("contract_id") != "WAM-PRIVACY-CORE003-STEP04-DRAFT-01":
        raise ValueError("contract id")
    if data.get("review_status") != "PROPOSED_UNAPPROVED":
        raise ValueError("cannot self-attest maintainer approval")
    if data.get("production_status") != "BLOCKED":
        raise ValueError("cannot close CORE-003 by design-only CI")
    for key in ("core_change_authorized", "activation_authorized", "maintainer_signoff"):
        if data.get(key) is not False:
            raise ValueError(f"unauthorized claim: {key}")
    if data.get("pins") != PINNED:
        raise ValueError("pinned source mismatch")
    c = data.get("current_implementation", {})
    if c.get("verifier_hook") != "READ_ONLY_REGTEST_RPC" or c.get("core_root_derivation") != "MISSING":
        raise ValueError("invalid current Core claims")
    if c.get("core_chainstate_mutation") != "NOT_IMPLEMENTED":
        raise ValueError("incorrect production/Core integration")
    if data.get("candidate_empty_block_rule") != "PENDING_MAINTAINER_DECISION":
        raise ValueError("empty block contract silently approved")
    if data.get("candidate_anchor_policy") != "PENDING_MAINTAINER_DECISION":
        raise ValueError("anchor history contract silently approved")
    forbidden = data.get("forbidden_inputs")
    required = {
        "TRUSTED_RPC_NEXT_ANCHOR", "RPC_SUPPLIED_NULLIFIER_AS_VERIFIED",
        "RPC_SUPPLIED_OUTPUT_COMMITMENT_AS_VERIFIED",
        "RPC_SUPPLIED_TX_DIGEST_FOR_CONSENSUS",
        "CLIENT_SUPPLIED_PREVIOUS_CHAIN_TIP_AS_AUTHORITY",
        "SNAPSHOT_MAC_AS_SOLE_ROLLBACK_PROTECTION",
    }
    if not isinstance(forbidden, list) or not required <= set(forbidden):
        raise ValueError("weakened trust boundary")
    api = data.get("candidate_api")
    names = [
        "parse_canonical_block", "verify_hardened_envelope",
        "stage_shielded_connect", "commit_block_atomically",
        "disconnect_exact_tip", "recover_and_replay",
    ]
    if not isinstance(api, list) or [a.get("name") for a in api] != names:
        raise ValueError("missing interface stage")
    if any(not x.get("owner") or not x.get("source") for x in api):
        raise ValueError("owner or trusted input unspecified")
    inv = data.get("invariants")
    if not isinstance(inv, list) or {v.get("id") for v in inv} != INV_IDS or len(inv) != len(INV_IDS):
        raise ValueError("missing invariant / duplicate id")
    for v in inv:
        if v.get("status") != "TEST_REQUIRED" or not v.get("negative_test"):
            raise ValueError("invented integration test pass")
    decisions = data.get("decisions")
    if not isinstance(decisions, list) or {x.get("id") for x in decisions} != DEC_IDS or len(decisions) != len(DEC_IDS):
        raise ValueError("missing maintainer decision / duplicate id")
    for d in decisions:
        if d.get("status") != "PENDING_MAINTAINER":
            raise ValueError("unattributed approval")
        if d.get("owner") != "WAM_CORE_MAINTAINER" or not d.get("options"):
            raise ValueError("missing maintainer ownership / options")
    evidence = data.get("evidence", {})
    required_missing = {
        "INDEPENDENT_CONSENSUS_SPEC", "REAL_PROOF_TO_DURABLE_CORE",
        "EXTERNAL_CRYPTO_AUDIT", "PHYSICAL_POWER_LOSS",
        "OPERATOR_TESTNET", "MAINNET_ACTIVATION",
        "MAINTAINER_APPROVAL",
    }
    if not required_missing <= set(evidence.get("not_demonstrated", [])):
        raise ValueError("hidden missing evidence")

def grounded_sources() -> None:
    """Assertions grounded in the frozen implementation; not proof of safety."""
    core = (ROOT / "prototypes/zk_balance_halo2/src/core_state.rs").read_text()
    wallet = (ROOT / "prototypes/zk_balance_halo2/src/wallet_state.rs").read_text()
    verifier = (ROOT / "integration/core/phase13b/privacy_verifier.cpp").read_text()
    patcher = (ROOT / "integration/core/phase13b/apply_generated_core.py").read_text()
    circuit = (ROOT / "prototypes/zk_balance_halo2/src/hardened_bundle.rs").read_text()
    journal = (ROOT / "v2/core003_research/tests/core003_step03.rs").read_text()
    for token in ("pub next_anchor: [u8; 32]", "self.current_anchor = block.next_anchor",
                  "verify_hardened_bundle_envelope_and_decode", "pub commitments:"):
        # Core uses a private HashSet, not a public ordered field.
        if token == "pub commitments:":
            if "commitments: HashSet<[u8; 32]>" not in core:
                raise ValueError("Core commitment storage changed")
        elif token not in core:
            raise ValueError("Core trust boundary drift: " + token)
    for token in ("pub fn root(&self) -> Fp", "TREE_CAPACITY", "pub fn process_block"):
        if token not in wallet:
            raise ValueError("wallet scanner reference drift")
    if "3, // Phase 13B: regtest only." not in verifier:
        raise ValueError("regtest hook changed")
    for token in ("verifyshieldedproof", "This RPC is read-only", "ChainType::REGTEST"):
        if token not in patcher:
            raise ValueError("generated Core hook reference drift")
    if "two public nullifiers" not in circuit or "two public output commitments" not in circuit:
        raise ValueError("2x2 circuit assumption drift")
    for token in ("AfterFileSyncBeforeRename", "AfterDirSyncBeforeAck", "RollbackDetected"):
        if token not in journal:
            raise ValueError("Step 03 crash fixture missing")
    if not DESIGN_PATH.exists() or DESIGN_PATH.read_text().count("CORE-003") < 4:
        raise ValueError("architecture review document missing")

class ContractReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    def test_draft_contract_and_grounded_references(self) -> None:
        check(self.data)
        grounded_sources()

    def test_cannot_promote_proposal_into_consensus_approval(self) -> None:
        for key, value in (("review_status", "APPROVED"), ("production_status", "PASS"),
                           ("maintainer_signoff", True), ("activation_authorized", True)):
            alt = copy.deepcopy(self.data)
            alt[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check(alt)

    def test_missing_security_invariant_and_maintainer_decision_fail_closed(self) -> None:
        for key in ("invariants", "decisions"):
            alt = copy.deepcopy(self.data)
            alt[key].pop()
            with self.subTest(key=key), self.assertRaises(ValueError):
                check(alt)

    def test_closing_anchor_empty_block_or_approval_without_evidence_fails(self) -> None:
        for key in ("candidate_empty_block_rule", "candidate_anchor_policy"):
            alt = copy.deepcopy(self.data)
            alt[key] = "ASSUME_SAFE"
            with self.subTest(key=key), self.assertRaises(ValueError):
                check(alt)
        alt = copy.deepcopy(self.data)
        alt["decisions"][0]["status"] = "APPROVED"
        with self.assertRaises(ValueError):
            check(alt)

    def test_root_provenance_and_snapshot_replay_limits_must_stay_visible(self) -> None:
        alt = copy.deepcopy(self.data)
        alt["forbidden_inputs"].remove("TRUSTED_RPC_NEXT_ANCHOR")
        with self.assertRaises(ValueError):
            check(alt)
        alt = copy.deepcopy(self.data)
        alt["evidence"]["not_demonstrated"].remove("EXTERNAL_CRYPTO_AUDIT")
        with self.assertRaises(ValueError):
            check(alt)

if __name__ == "__main__":
    unittest.main(verbosity=2)
