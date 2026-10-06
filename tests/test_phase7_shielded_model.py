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
    note_commitment,
    nullifier,
    spend_key_tag,
)


def b(n: int) -> bytes:
    return bytes([n]) * 32


def note(value: int, tag: int, rho: int, rseed: int, key: int = 9) -> Note:
    return Note(value, b(tag), spend_key_tag(b(key)), b(rho), b(rseed))


class ShieldedStateModelTests(unittest.TestCase):
    def test_shield_then_private_spend_then_unshield_conserves_value(self):
        n1 = note(100_000, 1, 2, 3, 9)
        r1 = apply_transition(
            ShieldedState(),
            Transition(outputs=(n1,), transparent_in=100_000),
        )
        self.assertEqual(r1.state.pool_atoms, 100_000)

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
            Note(5_000, b(1), spend_key_tag(b(9)), b(2), b(3), version=2).validate()

    def test_commitment_and_nullifier_vectors_are_deterministic(self):
        n = note(123_456, 1, 2, 3, 9)
        self.assertEqual(
            spend_key_tag(b(9)).hex(),
            "f2567f84f1e755c52d663d94de9ba8f04c158555590adcff9834bbd9f7b1f09d",
        )
        self.assertEqual(
            note_commitment(n).hex(),
            "c7c3afaefd212cc7bcf174e85af72d83a6df9bffca97c953ea981e386f44da52",
        )
        self.assertEqual(
            nullifier(n, b(9)).hex(),
            "a7ec9d54f8c851a66ee619622f7a143a2d0e57aa3d6a018ff4de4f28a4a3eeba",
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
