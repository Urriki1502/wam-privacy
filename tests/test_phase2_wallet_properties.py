import random
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from wallet_privacy import Coin, Intent, Policy, PolicyError, redacted_event, select_coins


def make_coin(rng, idx):
    return Coin(
        txid=f"{idx + 1:064x}",
        vout=rng.randrange(0, 4),
        atoms=rng.randrange(1_000, 200_000),
        cluster=f"cluster-{rng.randrange(0, 4)}",
        confirmations=rng.randrange(0, 20),
        reserved=rng.randrange(0, 8) == 0,
    )


class WalletPrivacyPropertyTests(unittest.TestCase):
    def test_seeded_policy_invariants(self):
        rng = random.Random(0x57414D5052495641)  # "WAMPRIVA"

        for case in range(500):
            coins = [make_coin(rng, case * 40 + i) for i in range(rng.randrange(1, 30))]
            intent = Intent(f"recipient-{case}", rng.randrange(330, 250_000))
            fee = rng.randrange(1, 5_000)
            policy = Policy(
                min_confirmations=rng.randrange(0, 4),
                allow_cluster_merge=bool(rng.randrange(0, 2)),
                max_inputs=rng.randrange(1, 20),
                exact_search_limit=rng.randrange(4, 19),
                exact_search_width=rng.randrange(1, 5),
            )

            try:
                result = select_coins(coins, [intent], fee, policy)
            except PolicyError:
                continue

            selected = result.selected
            self.assertTrue(selected)
            self.assertLessEqual(len(selected), policy.max_inputs)
            self.assertEqual(
                len({c.outpoint for c in selected}),
                len(selected),
            )
            self.assertTrue(all(not c.reserved for c in selected))
            self.assertTrue(
                all(c.confirmations >= policy.min_confirmations for c in selected)
            )
            self.assertGreaterEqual(result.total_input_atoms, result.target_atoms + fee)
            self.assertIn(
                result.change_atoms,
                (0,) if result.change_atoms == 0 else (result.change_atoms,),
            )
            self.assertTrue(
                result.change_atoms == 0 or result.change_atoms >= policy.dust_threshold
            )

            if not policy.allow_cluster_merge:
                self.assertEqual(len(result.clusters), 1)
                self.assertNotIn("CLUSTER_MERGE", result.warnings)

            # Input order must not alter the decision.
            shuffled = list(coins)
            rng.shuffle(shuffled)
            again = select_coins(shuffled, [intent], fee, policy)
            self.assertEqual(
                tuple(c.outpoint for c in selected),
                tuple(c.outpoint for c in again.selected),
            )

            event = redacted_event(result)
            rendered = repr(event)
            for c in selected:
                self.assertNotIn(c.txid, rendered)
                self.assertNotIn(c.cluster, rendered)
            self.assertNotIn(intent.recipient, rendered)

    def test_merge_warning_iff_multiple_clusters_selected(self):
        result = select_coins(
            [
                Coin(f"{1:064x}", 0, 25_000, "a", 10),
                Coin(f"{2:064x}", 0, 27_000, "b", 10),
            ],
            [Intent("recipient", 50_000)],
            1_000,
            Policy(allow_cluster_merge=True),
        )
        self.assertEqual("CLUSTER_MERGE" in result.warnings, len(result.clusters) > 1)

    def test_change_warning_iff_change_exists(self):
        exact = select_coins(
            [Coin(f"{1:064x}", 0, 51_000, "a", 10)],
            [Intent("recipient", 50_000)],
            1_000,
        )
        change = select_coins(
            [Coin(f"{2:064x}", 0, 60_000, "a", 10)],
            [Intent("recipient", 50_000)],
            1_000,
        )
        self.assertEqual("CHANGE_CREATED" in exact.warnings, exact.change_atoms > 0)
        self.assertEqual("CHANGE_CREATED" in change.warnings, change.change_atoms > 0)


if __name__ == "__main__":
    unittest.main()
