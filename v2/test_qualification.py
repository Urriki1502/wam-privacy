"""V2-05 negative validation of acceptance index. No network access."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from v2.qualify_v2 import expected_ids, validate_matrix

ROOT = Path(__file__).resolve().parents[1]


class AcceptanceIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "v2/acceptance_matrix.json").read_text(
            encoding="utf-8"
        ))

    def test_exact_29_ids_and_existing_fixture_references(self):
        result = validate_matrix(self.data, ROOT)
        self.assertEqual(result["cases"], 29)
        self.assertEqual({c["id"] for c in self.data["cases"]}, expected_ids())
        self.assertEqual(result["categories"]["BLOCKED"], 1)

    def test_cannot_delete_a_case_or_add_duplicate(self):
        for changed in (
            {**deepcopy(self.data), "cases": deepcopy(self.data["cases"])[:-1]},
            {**deepcopy(self.data), "cases": deepcopy(self.data["cases"])[:-1] + [
                deepcopy(self.data["cases"][0])
            ]},
        ):
            with self.assertRaisesRegex(ValueError, "V2_05_REJECTED"):
                validate_matrix(changed, ROOT)

    def test_reject_fake_test_evidence(self):
        changed = deepcopy(self.data)
        changed["cases"][0]["evidence_tests"] = ["test_nonexistent_green_signal"]
        with self.assertRaisesRegex(ValueError, "test symbol not found"):
            validate_matrix(changed, ROOT)

    def test_cannot_upgrade_production_or_external_audit(self):
        for key in ("production", "external_audit", "mainnet_activation"):
            changed = deepcopy(self.data)
            changed["claims"][key] = True
            with self.assertRaisesRegex(ValueError, "forbidden security claim"):
                validate_matrix(changed, ROOT)

    def test_core003_is_not_a_pass(self):
        changed = deepcopy(self.data)
        target = next(x for x in changed["cases"] if x["id"] == "CORE-003")
        target["evidence_class"] = "FIXTURE_ONLY"
        with self.assertRaisesRegex(ValueError, "CORE-003 must remain blocked"):
            validate_matrix(changed, ROOT)

    def test_unknown_status_and_fabricated_path_rejected(self):
        changed = deepcopy(self.data)
        changed["cases"][0]["evidence_paths"] = ["v2/fictional-success.txt"]
        with self.assertRaisesRegex(ValueError, "missing evidence"):
            validate_matrix(changed, ROOT)
        changed = deepcopy(self.data)
        changed["cases"][0]["evidence_class"] = "PRODUCTION_PASS"
        with self.assertRaisesRegex(ValueError, "unknown class"):
            validate_matrix(changed, ROOT)


if __name__ == "__main__":
    unittest.main()
