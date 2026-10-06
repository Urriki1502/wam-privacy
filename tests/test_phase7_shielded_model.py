import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from shielded_model import (
    Note,
    Spend,
    ShieldedState,
    Transition,
    apply_transition,
    can_view,
    commitment_root,
    note_commitment,
    nullifier,
    spend_key_tag,
    view_note,
    view_tag,
)


def b(n: int) -> bytes:
    return bytes([n]) * 32


def note(value: int, view: int, rho: int, rseed: int, key: int = 9) -> Note:
    return Note(value, view_tag(b(view), b(rho)), spend_key_tag(b(key)), b(rho), b(rseed))


class ShieldedStateModelTests(unittest.TestCase):
    def test_shield_then_private_spend_then_unshield_conserves_value(self):
        n1 = note(100_000, 1, 2, 3, 9)
        r1 = apply_transition(
            ShieldedState(),
            Transition(outputs=(n1,), transparent_in=100_000),
        )
        self.assertEqual(r1.state.pool_atoms, 100_000)
        self.assertNotEqual(r1.prior_root, r1.new_root)

        n2 = note(74_000, 4, 5, 6, 8)
        r2 = apply_transition(
            r1.state,
            Transition(
                spends=(Spend(n1, b(9)),),
                outputs=(n2,),
                transparent_out=25_000,
                fee_atoms=1_000,
            ),
        )
        self.assertEqual(r2.conservation_lhs, r2.conservation_rhs)
        self.assertEqual(r2.state.pool_atoms, 75_000)
        self.assertIn(nullifier(n1, b(9)), r2.state.nullifiers)

    def test_view_key_recognizes_note_without_spend_authority(self):
        n1 = note(10_000, 1, 2, 3, 9)
        self.assertTrue(can_view(n1, b(1)))
        self.assertFalse(can_view(n1, b(2)))
        self.assertEqual(view_note(n1, b(1))["value"], 10_000)
        self.assertIsNone(view_note(n1, b(2)))
        with self.assertRaisesRegex(ValueError, "^SPEND_AUTHORITY_MISMATCH$"):
            nullifier(n1, b(1))

    def test_double_spend_nullifier_is_rejected(self):
        n1 = note(10_000, 1, 2, 3, 7)
        initial = apply_transition(
            ShieldedState(),
            Transition(outputs=(n1,), transparent_in=10_000),
        ).state
        first = apply_transition(
            initial,
            Transition(
                spends=(Spend(n1, b(7)),),
                transparent_out=9_000,
                fee_atoms=1_000,
            ),
        ).state
        with self.assertRaisesRegex(ValueError, "^NULLIFIER_ALREADY_USED$"):
            apply_transition(
                first,
                Transition(
                    spends=(Spend(n1, b(7)),),
                    transparent_out=9_000,
                    fee_atoms=1_000,
                ),
            )

    def test_alternate_key_cannot_create_second_nullifier_for_same_note(self):
        n1 = note(10_000, 1, 2, 3, 7)
        state = apply_transition(
            ShieldedState(),
            Transition(outputs=(n1,), transparent_in=10_000),
        ).state
        with self.assertRaisesRegex(ValueError, "^SPEND_AUTHORITY_MISMATCH$"):
            apply_transition(
                state,
                Transition(
                    spends=(Spend(n1, b(8)),),
                    transparent_out=9_000,
                    fee_atoms=1_000,
                ),
            )

    def test_note_must_exist_in_commitment_state(self):
        ghost = note(10_000, 1, 2, 3, 7)
        with self.assertRaisesRegex(ValueError, "^NOTE_NOT_IN_STATE$"):
            apply_transition(
                ShieldedState(pool_atoms=10_000),
                Transition(
                    spends=(Spend(ghost, b(7)),),
                    transparent_out=9_000,
                    fee_atoms=1_000,
                ),
            )

    def test_inflation_attempt_fails_value_conservation(self):
        source = note(10_000, 1, 2, 3, 7)
        initial = apply_transition(
            ShieldedState(),
            Transition(outputs=(source,), transparent_in=10_000),
        ).state
        inflated = note(11_000, 4, 5, 6, 8)
        with self.assertRaisesRegex(ValueError, "^VALUE_CONSERVATION$"):
            apply_transition(
                initial,
                Transition(
                    spends=(Spend(source, b(7)),),
                    outputs=(inflated,),
                    fee_atoms=1,
                ),
            )

    def test_unshield_without_value_fails_conservation(self):
        with self.assertRaisesRegex(ValueError, "^VALUE_CONSERVATION$"):
            apply_transition(
                ShieldedState(),
                Transition(transparent_out=1),
            )

    def test_duplicate_output_commitment_rejected(self):
        n = note(5_000, 1, 2, 3)
        with self.assertRaisesRegex(ValueError, "^DUPLICATE_OUTPUT_COMMITMENT$"):
            apply_transition(
                ShieldedState(),
                Transition(outputs=(n, n), transparent_in=10_000),
            )

    def test_protocol_version_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "^UNSUPPORTED_NOTE_VERSION$"):
            Note(
                5_000,
                view_tag(b(1), b(2)),
                spend_key_tag(b(9)),
                b(2),
                b(3),
                version=2,
            ).validate()

    def test_commitment_nullifier_view_and_root_vectors_are_deterministic(self):
        n = note(123_456, 1, 2, 3, 9)
        self.assertEqual(
            view_tag(b(1), b(2)).hex(),
            "d95c3458a0a3fc0300f132495bd19cb9e14461513da1250a8e61b9c51c1fa7b3",
        )
        self.assertEqual(
            spend_key_tag(b(9)).hex(),
            "f2567f84f1e755c52d663d94de9ba8f04c158555590adcff9834bbd9f7b1f09d",
        )
        self.assertEqual(
            note_commitment(n).hex(),
            "543093ccf64caae02c58cd6043a2b854610d214358247103abf2e42e11e9f229",
        )
        self.assertEqual(
            nullifier(n, b(9)).hex(),
            "e88a53d585ac9c4c90d2eab1e5397278e87db37697b9bfcae819b2e97a6721eb",
        )
        self.assertEqual(
            commitment_root((n.commitment,)).hex(),
            "5186e4469a17735b27769ce91ce7304b3052442b16d57fe5c6e6ae19ebe5eb87",
        )

    def test_state_replay_with_same_output_is_rejected(self):
        n = note(5_000, 1, 2, 3)
        state = apply_transition(
            ShieldedState(),
            Transition(outputs=(n,), transparent_in=5_000),
        ).state
        with self.assertRaisesRegex(ValueError, "^COMMITMENT_ALREADY_EXISTS$"):
            apply_transition(
                state,
                Transition(outputs=(n,), transparent_in=5_000),
            )


if __name__ == "__main__":
    unittest.main()
