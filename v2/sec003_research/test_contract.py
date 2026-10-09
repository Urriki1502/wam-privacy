"""Contract-level negative/restart matrix. NOT A/B integration evidence."""
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from v2.sec003_research.contract import Phase, Record, recover, next_phase


class RecoveryContractTests(unittest.TestCase):
    def record(self, phase=Phase.PREPARED, **kw):
        values = dict(transaction_id="tx-local", request_binding="bound-request",
                      phase=phase, policy_generation=7)
        values.update(kw)
        return Record(**values)

    def decision(self, record=None, **kw):
        values = dict(trusted_policy_generation=7, policy_consumed=False,
                      signer_state="ABSENT")
        values.update(kw)
        return recover(record or self.record(), **values)

    def test_fault_matrix_after_every_durable_stage_and_restart(self):
        cases = [
            (Phase.PREPARED, False, "ABSENT", "REAUTHORIZE"),
            (Phase.PREPARED, True, "ABSENT", "REAUTHORIZE"),
            (Phase.POLICY_SPENT, True, "ABSENT", "REAUTHORIZE"),
            (Phase.SIGNER_RESERVED, True, "RESERVED", "BLOCKED"),
            (Phase.SIGNER_RESERVED, True, "COMPLETE", "RETURN_DURABLE_RESULT"),
            (Phase.COMPLETE, True, "COMPLETE", "RETURN_DURABLE_RESULT"),
        ]
        for phase, spent, signer, expected in cases:
            with self.subTest(phase=phase, signer=signer):
                record = self.record(phase)
                # Serialize/reload an intent at each crash cut; model only.
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "intent.json"
                    path.write_text(json.dumps(asdict(record)))
                    reloaded = json.loads(path.read_text())
                    reloaded["phase"] = Phase(reloaded["phase"])
                    restarted = Record(**reloaded)
                self.assertEqual(self.decision(restarted, policy_consumed=spent,
                                 signer_state=signer, signer_binding="bound-request",
                                 result_binding="result-1"), expected)

    def test_uncertain_provider_outcome_never_retries(self):
        for phase in Phase:
            self.assertEqual(self.decision(self.record(phase), policy_consumed=True,
                             signer_state="RESERVED", signer_binding="bound-request"),
                             "BLOCKED")

    def test_disappeared_reservation_or_result_blocks(self):
        for phase in (Phase.SIGNER_RESERVED, Phase.COMPLETE):
            self.assertEqual(self.decision(self.record(phase), policy_consumed=True),
                             "BLOCKED")

    def test_policy_rollback_blocks(self):
        self.assertEqual(self.decision(trusted_policy_generation=6), "BLOCKED")
        self.assertEqual(self.decision(self.record(Phase.POLICY_SPENT)), "BLOCKED")
        self.assertEqual(self.decision(self.record(Phase.COMPLETE),
                         signer_state="COMPLETE", signer_binding="bound-request",
                         result_binding="result-1"), "BLOCKED")

    def test_swapped_request_or_result_receipt_blocks(self):
        record = self.record(Phase.COMPLETE, signer_binding="bound-request",
                             result_binding="result-1")
        self.assertEqual(self.decision(record, policy_consumed=True,
                         signer_state="COMPLETE", signer_binding="other",
                         result_binding="result-1"), "BLOCKED")
        self.assertEqual(self.decision(record, policy_consumed=True,
                         signer_state="COMPLETE", signer_binding="bound-request",
                         result_binding="other"), "BLOCKED")

    def test_impossible_early_completion_blocks(self):
        for phase in (Phase.PREPARED, Phase.POLICY_SPENT):
            self.assertEqual(self.decision(self.record(phase), policy_consumed=True,
                             signer_state="COMPLETE", signer_binding="bound-request",
                             result_binding="result-1"), "BLOCKED")

    def test_invalid_witness_blocks(self):
        for generation in (-1, True, "7", None):
            self.assertEqual(self.decision(trusted_policy_generation=generation),
                             "BLOCKED")
        for phase in ("COMPLETE", None, 2):
            self.assertEqual(self.decision(self.record(phase)), "BLOCKED")
        self.assertEqual(self.decision(signer_state="UNKNOWN"), "BLOCKED")
        self.assertEqual(self.decision(policy_consumed=1), "BLOCKED")

    def test_phases_cannot_skip_or_rewind(self):
        phases = list(Phase)
        for i, current in enumerate(phases):
            for j, proposed in enumerate(phases):
                if j == i + 1:
                    self.assertEqual(next_phase(current, proposed), proposed)
                else:
                    with self.assertRaises(ValueError):
                        next_phase(current, proposed)


if __name__ == "__main__":
    unittest.main()
