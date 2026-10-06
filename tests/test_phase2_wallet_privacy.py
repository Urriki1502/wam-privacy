import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from wallet_privacy import Coin, Intent, Policy, PolicyError, redacted_event, select_coins


def coin(n, amount, cluster="a", confirmations=10, reserved=False):
    return Coin(
        txid=f"{n:064x}",
        vout=0,
        atoms=amount,
        cluster=cluster,
        confirmations=confirmations,
        reserved=reserved,
    )


class WalletPrivacyPolicyTests(unittest.TestCase):
    def test_exact_match_preferred_over_change(self):
        result = select_coins(
            [coin(1, 51_000), coin(2, 60_000)],
            [Intent("recipient", 50_000)],
            1_000,
        )
        self.assertEqual([c.txid for c in result.selected], [f"{1:064x}"])
        self.assertEqual(result.change_atoms, 0)
        self.assertEqual(result.warnings, ())

    def test_cluster_merge_is_forbidden_by_default(self):
        with self.assertRaisesRegex(PolicyError, "^INSUFFICIENT_SINGLE_CLUSTER_FUNDS$"):
            select_coins(
                [coin(1, 30_000, "a"), coin(2, 30_000, "b")],
                [Intent("recipient", 50_000)],
                1_000,
            )

    def test_cluster_merge_requires_explicit_policy(self):
        result = select_coins(
            [coin(1, 30_000, "a"), coin(2, 30_000, "b")],
            [Intent("recipient", 50_000)],
            1_000,
            Policy(allow_cluster_merge=True),
        )
        self.assertEqual(len(result.clusters), 2)
        self.assertIn("CLUSTER_MERGE", result.warnings)
        self.assertIn("CHANGE_CREATED", result.warnings)

    def test_reserved_and_underconfirmed_coins_are_excluded(self):
        result = select_coins(
            [
                coin(1, 51_000, reserved=True),
                coin(2, 51_000, confirmations=0),
                coin(3, 51_000),
            ],
            [Intent("recipient", 50_000)],
            1_000,
        )
        self.assertEqual(result.selected, (coin(3, 51_000),))

    def test_dust_change_is_not_created(self):
        with self.assertRaisesRegex(PolicyError, "^INSUFFICIENT_FUNDS_OR_DUST_CHANGE$"):
            select_coins(
                [coin(1, 51_100)],
                [Intent("recipient", 50_000)],
                1_000,
            )

    def test_exact_two_input_match_can_beat_one_input_change(self):
        result = select_coins(
            [coin(1, 20_000), coin(2, 31_000), coin(3, 60_000)],
            [Intent("recipient", 50_000)],
            1_000,
        )
        self.assertEqual({c.atoms for c in result.selected}, {20_000, 31_000})
        self.assertEqual(result.change_atoms, 0)

    def test_selection_is_deterministic_across_input_order(self):
        coins = [coin(3, 60_000), coin(1, 20_000), coin(2, 31_000)]
        a = select_coins(coins, [Intent("recipient", 50_000)], 1_000)
        b = select_coins(list(reversed(coins)), [Intent("recipient", 50_000)], 1_000)
        self.assertEqual(tuple(c.outpoint for c in a.selected), tuple(c.outpoint for c in b.selected))

    def test_duplicate_outpoint_fails_closed(self):
        duplicate = coin(1, 30_000)
        with self.assertRaisesRegex(PolicyError, "^DUPLICATE_OUTPOINT$"):
            select_coins(
                [duplicate, duplicate],
                [Intent("recipient", 10_000)],
                1_000,
            )

    def test_max_input_policy_is_enforced(self):
        with self.assertRaisesRegex(PolicyError, "^INSUFFICIENT_FUNDS_OR_DUST_CHANGE$"):
            select_coins(
                [coin(i + 1, 10_000) for i in range(6)],
                [Intent("recipient", 49_000)],
                1_000,
                Policy(max_inputs=4),
            )

    def test_redacted_event_contains_no_sensitive_identifiers_or_amounts(self):
        result = select_coins(
            [coin(1, 51_000, "private-cluster-name")],
            [Intent("recipient-secret", 50_000)],
            1_000,
        )
        event = redacted_event(result)
        rendered = repr(event)
        self.assertNotIn(f"{1:064x}", rendered)
        self.assertNotIn("private-cluster-name", rendered)
        self.assertNotIn("recipient-secret", rendered)
        self.assertNotIn("50000", rendered)
        self.assertNotIn("51000", rendered)
        self.assertEqual(
            set(event),
            {"schema", "selected_inputs", "cluster_count", "change_created", "warning_codes"},
        )


if __name__ == "__main__":
    unittest.main()
