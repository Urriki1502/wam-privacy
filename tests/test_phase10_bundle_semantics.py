import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from shielded_model import (
    MAX_ATOMS,
    Note,
    Spend,
    ShieldedState,
    Transition,
    apply_transition,
    nullifier,
    spend_key_tag,
    view_tag,
)


def b(n: int) -> bytes:
    return bytes([n]) * 32


def note(value: int, view: int, rho: int, rseed: int, key: int) -> Note:
    return Note(value, view_tag(b(view), b(rho)), spend_key_tag(b(key)), b(rho), b(rseed))


class Phase10BundleSemanticsTests(unittest.TestCase):
    def test_two_input_two_output_bundle_conserves_and_updates_pool(self):
        a = note(40_000, 1, 11, 21, 31)
        bnote = note(60_000, 2, 12, 22, 32)
        initial = apply_transition(
            ShieldedState(),
            Transition(outputs=(a, bnote), transparent_in=100_000),
        ).state

        c = note(55_000, 3, 13, 23, 33)
        d = note(40_000, 4, 14, 24, 34)
        result = apply_transition(
            initial,
            Transition(
                spends=(Spend(a, b(31)), Spend(bnote, b(32))),
                outputs=(c, d),
                fee_atoms=5_000,
            ),
        )

        self.assertEqual(result.spent_atoms, 100_000)
        self.assertEqual(result.created_atoms, 95_000)
        self.assertEqual(result.conservation_lhs, result.conservation_rhs)
        self.assertEqual(result.state.pool_atoms, 95_000)
        self.assertIn(nullifier(a, b(31)), result.state.nullifiers)
        self.assertIn(nullifier(bnote, b(32)), result.state.nullifiers)

    def test_duplicate_input_inside_bundle_is_rejected(self):
        a = note(50_000, 1, 11, 21, 31)
        state = apply_transition(
            ShieldedState(),
            Transition(outputs=(a,), transparent_in=50_000),
        ).state

        with self.assertRaisesRegex(ValueError, "^NULLIFIER_ALREADY_USED$"):
            apply_transition(
                state,
                Transition(
                    spends=(Spend(a, b(31)), Spend(a, b(31))),
                    outputs=(note(99_000, 2, 12, 22, 32),),
                    fee_atoms=1_000,
                ),
            )

    def test_mixed_bundle_accounts_transparent_flow_and_fee(self):
        a = note(40_000, 1, 11, 21, 31)
        bnote = note(60_000, 2, 12, 22, 32)
        state = apply_transition(
            ShieldedState(),
            Transition(outputs=(a, bnote), transparent_in=100_000),
        ).state

        out1 = note(70_000, 3, 13, 23, 33)
        out2 = note(40_000, 4, 14, 24, 34)
        result = apply_transition(
            state,
            Transition(
                spends=(Spend(a, b(31)), Spend(bnote, b(32))),
                outputs=(out1, out2),
                transparent_in=20_000,
                transparent_out=5_000,
                fee_atoms=5_000,
            ),
        )

        self.assertEqual(result.conservation_lhs, 120_000)
        self.assertEqual(result.conservation_rhs, 120_000)
        self.assertEqual(result.state.pool_atoms, 110_000)

    def test_fee_cannot_leave_phantom_pool_value(self):
        a = note(100_000, 1, 11, 21, 31)
        state = apply_transition(
            ShieldedState(),
            Transition(outputs=(a,), transparent_in=100_000),
        ).state
        out = note(99_000, 2, 12, 22, 32)

        result = apply_transition(
            state,
            Transition(
                spends=(Spend(a, b(31)),),
                outputs=(out,),
                fee_atoms=1_000,
            ),
        )
        self.assertEqual(result.state.pool_atoms, 99_000)

    def test_spends_cannot_exceed_declared_pool_balance(self):
        a = note(100_000, 1, 11, 21, 31)
        malformed = ShieldedState(
            commitments=(a.commitment,),
            pool_atoms=10_000,
        )
        with self.assertRaisesRegex(ValueError, "^POOL_SPEND_EXCEEDS_BALANCE$"):
            apply_transition(
                malformed,
                Transition(
                    spends=(Spend(a, b(31)),),
                    outputs=(note(99_000, 2, 12, 22, 32),),
                    fee_atoms=1_000,
                ),
            )

    def test_bundle_global_pool_cannot_exceed_wam_cap(self):
        source = note(MAX_ATOMS, 1, 11, 21, 31)
        state = ShieldedState(
            commitments=(source.commitment,),
            pool_atoms=MAX_ATOMS,
        )
        out1 = note(MAX_ATOMS, 2, 12, 22, 32)
        out2 = note(MAX_ATOMS, 3, 13, 23, 33)

        with self.assertRaisesRegex(ValueError, "^AMOUNT_RANGE$"):
            apply_transition(
                state,
                Transition(
                    spends=(Spend(source, b(31)),),
                    outputs=(out1, out2),
                    transparent_in=MAX_ATOMS,
                ),
            )

    def test_bundle_transition_limit_fails_closed(self):
        n = note(1, 1, 11, 21, 31)
        with self.assertRaisesRegex(ValueError, "^TRANSITION_LIMIT$"):
            Transition(outputs=(n,) * 257, transparent_in=257).validate_shape()


if __name__ == "__main__":
    unittest.main()
