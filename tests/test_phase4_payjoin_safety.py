import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from payjoin_safety import (
    PayjoinContext,
    PayjoinError,
    Transaction,
    TxInput,
    TxOutput,
    redacted_payjoin_event,
    validate_proposal,
)


def sender_input(n=1, atoms=100_000, sequence=0xFFFFFFFD, **kw):
    return TxInput(
        txid=f"{n:064x}",
        vout=0,
        atoms=atoms,
        owner="sender",
        sequence=sequence,
        finalized=kw.get("finalized", False),
        utxo_present=True,
        has_keypaths=kw.get("has_keypaths", False),
        has_partial_signature=kw.get("has_partial_signature", False),
    )


def receiver_input(n=9, atoms=20_000, **kw):
    return TxInput(
        txid=f"{n:064x}",
        vout=0,
        atoms=atoms,
        owner=kw.get("owner", "receiver"),
        sequence=0xFFFFFFFD,
        finalized=kw.get("finalized", True),
        utxo_present=kw.get("utxo_present", True),
        has_keypaths=kw.get("has_keypaths", False),
        has_partial_signature=kw.get("has_partial_signature", False),
    )


def original():
    return Transaction(
        version=2,
        locktime=0,
        inputs=(sender_input(atoms=100_000),),
        outputs=(
            TxOutput("receiver-payment", 50_000, "receiver"),
            TxOutput("sender-change", 49_000, "sender"),
        ),
    )


def proposal(
    *,
    recv_atoms=20_000,
    payment=69_000,
    change=49_000,
    version=2,
    locktime=0,
    recv_finalized=True,
    recv_utxo=True,
    sender_sequence=0xFFFFFFFD,
    sender_finalized=False,
    payment_destination="receiver-payment",
):
    return Transaction(
        version=version,
        locktime=locktime,
        inputs=(
            sender_input(
                atoms=100_000,
                sequence=sender_sequence,
                finalized=sender_finalized,
            ),
            receiver_input(
                atoms=recv_atoms,
                finalized=recv_finalized,
                utxo_present=recv_utxo,
            ),
        ),
        outputs=(
            TxOutput(payment_destination, payment, "receiver"),
            TxOutput("sender-change", change, "sender"),
        ),
    )


class PayjoinSafetyTests(unittest.TestCase):
    def test_valid_strict_proposal(self):
        evidence = validate_proposal(
            original(),
            proposal(),
            PayjoinContext(payment_output_index=0),
        )
        self.assertEqual(evidence["result"], "PASS")
        self.assertEqual(evidence["receiver_inputs_added"], 1)

    def test_original_input_cannot_be_removed(self):
        bad = Transaction(
            version=2,
            locktime=0,
            inputs=(receiver_input(),),
            outputs=proposal().outputs,
        )
        with self.assertRaisesRegex(PayjoinError, "^ORIGINAL_INPUT_REMOVED$"):
            validate_proposal(original(), bad, PayjoinContext(payment_output_index=0))

    def test_sender_sequence_cannot_change(self):
        with self.assertRaisesRegex(PayjoinError, "^SENDER_SEQUENCE_CHANGED$"):
            validate_proposal(
                original(),
                proposal(sender_sequence=1),
                PayjoinContext(payment_output_index=0),
            )

    def test_sender_input_must_not_be_finalized_in_proposal(self):
        with self.assertRaisesRegex(PayjoinError, "^SENDER_INPUT_FINALIZED$"):
            validate_proposal(
                original(),
                proposal(sender_finalized=True),
                PayjoinContext(payment_output_index=0),
            )

    def test_receiver_input_must_be_finalized_and_have_utxo(self):
        with self.assertRaisesRegex(PayjoinError, "^RECEIVER_INPUT_NOT_FINALIZED$"):
            validate_proposal(
                original(),
                proposal(recv_finalized=False),
                PayjoinContext(payment_output_index=0),
            )
        with self.assertRaisesRegex(PayjoinError, "^RECEIVER_INPUT_UTXO_MISSING$"):
            validate_proposal(
                original(),
                proposal(recv_utxo=False),
                PayjoinContext(payment_output_index=0),
            )

    def test_version_and_locktime_are_pinned(self):
        with self.assertRaisesRegex(PayjoinError, "^VERSION_CHANGED$"):
            validate_proposal(
                original(),
                proposal(version=3),
                PayjoinContext(payment_output_index=0),
            )
        with self.assertRaisesRegex(PayjoinError, "^LOCKTIME_CHANGED$"):
            validate_proposal(
                original(),
                proposal(locktime=1),
                PayjoinContext(payment_output_index=0),
            )

    def test_payment_substitution_disabled_by_default(self):
        with self.assertRaisesRegex(PayjoinError, "^PAYMENT_OUTPUT_SUBSTITUTED$"):
            validate_proposal(
                original(),
                proposal(payment_destination="different-receiver"),
                PayjoinContext(payment_output_index=0),
            )

    def test_payment_amount_cannot_decrease(self):
        # Keep transaction balanced while attempting to reduce receiver payment.
        bad = proposal(payment=49_000, change=49_000, recv_atoms=0)
        # recv_atoms=0 is invalid input shape; construct explicit malicious shape.
        bad = Transaction(
            version=2,
            locktime=0,
            inputs=(sender_input(atoms=100_000), receiver_input(atoms=1_000)),
            outputs=(
                TxOutput("receiver-payment", 49_000, "receiver"),
                TxOutput("sender-change", 49_000, "sender"),
            ),
        )
        with self.assertRaisesRegex(PayjoinError, "^PAYMENT_AMOUNT_DECREASED$"):
            validate_proposal(original(), bad, PayjoinContext(payment_output_index=0))

    def test_sender_change_is_protected_without_fee_contribution(self):
        with self.assertRaisesRegex(PayjoinError, "^PROTECTED_OUTPUT_CHANGED$"):
            validate_proposal(
                original(),
                proposal(change=48_000, payment=70_000),
                PayjoinContext(payment_output_index=0),
            )

    def test_explicit_fee_contribution_is_bounded(self):
        ok = validate_proposal(
            original(),
            proposal(change=48_500, payment=69_000),
            PayjoinContext(
                payment_output_index=0,
                fee_contribution_output_index=1,
                max_additional_fee_contribution=500,
            ),
        )
        self.assertTrue(ok["sender_fee_contribution_used"])

        with self.assertRaisesRegex(PayjoinError, "^FEE_CONTRIBUTION_EXCEEDED$"):
            validate_proposal(
                original(),
                proposal(change=48_000, payment=69_000),
                PayjoinContext(
                    payment_output_index=0,
                    fee_contribution_output_index=1,
                    max_additional_fee_contribution=500,
                ),
            )

    def test_absolute_fee_cannot_decrease(self):
        # Original fee = 1000. Proposal below has fee 500.
        bad = Transaction(
            version=2,
            locktime=0,
            inputs=(sender_input(atoms=100_000), receiver_input(atoms=20_000)),
            outputs=(
                TxOutput("receiver-payment", 70_500, "receiver"),
                TxOutput("sender-change", 49_000, "sender"),
            ),
        )
        with self.assertRaisesRegex(PayjoinError, "^ABSOLUTE_FEE_DECREASED$"):
            validate_proposal(original(), bad, PayjoinContext(payment_output_index=0))

    def test_keypaths_and_partial_signatures_fail_closed(self):
        bad_keypath = Transaction(
            2,
            0,
            (
                sender_input(atoms=100_000),
                receiver_input(has_keypaths=True),
            ),
            proposal().outputs,
        )
        with self.assertRaisesRegex(PayjoinError, "^INPUT_KEYPATH_PRESENT$"):
            validate_proposal(original(), bad_keypath, PayjoinContext(payment_output_index=0))

        bad_partial = Transaction(
            2,
            0,
            (
                sender_input(atoms=100_000),
                receiver_input(has_partial_signature=True),
            ),
            proposal().outputs,
        )
        with self.assertRaisesRegex(PayjoinError, "^INPUT_PARTIAL_SIGNATURE_PRESENT$"):
            validate_proposal(original(), bad_partial, PayjoinContext(payment_output_index=0))

    def test_receiver_batch_outputs_fail_closed_in_v01(self):
        bad = Transaction(
            version=2,
            locktime=0,
            inputs=(sender_input(atoms=100_000), receiver_input(atoms=30_000)),
            outputs=(
                TxOutput("receiver-payment", 69_000, "receiver"),
                TxOutput("sender-change", 49_000, "sender"),
                TxOutput("third-party", 10_000, "external"),
            ),
        )
        with self.assertRaisesRegex(PayjoinError, "^OUTPUT_COUNT_CHANGED$"):
            validate_proposal(original(), bad, PayjoinContext(payment_output_index=0))

    def test_receiver_value_is_conserved_in_valid_profile(self):
        before = original()
        after = proposal()
        evidence = validate_proposal(
            before,
            after,
            PayjoinContext(payment_output_index=0),
        )
        receiver_input = sum(i.atoms for i in after.inputs if i.owner == "receiver")
        payment_increase = after.outputs[0].atoms - before.outputs[0].atoms
        fee_increase = after.fee_atoms - before.fee_atoms
        self.assertEqual(receiver_input, payment_increase + fee_increase)
        self.assertEqual(evidence["result"], "PASS")

    def test_redacted_event_has_no_identifiers_or_amounts(self):
        evidence = validate_proposal(
            original(),
            proposal(),
            PayjoinContext(payment_output_index=0),
        )
        event = redacted_payjoin_event(evidence)
        rendered = repr(event)
        for value in (
            "receiver-payment",
            "sender-change",
            f"{1:064x}",
            f"{9:064x}",
            "69000",
            "49000",
        ):
            self.assertNotIn(value, rendered)


if __name__ == "__main__":
    unittest.main()
