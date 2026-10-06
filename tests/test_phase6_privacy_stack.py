import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from network_privacy import Endpoint, NetworkPlan, NetworkPolicy
from payjoin_safety import PayjoinContext, Transaction, TxInput, TxOutput
from privacy_stack import StackError, authorize_payjoin_stack, redacted_stack_event
from signer_abstraction import Approval, FixtureSigner, PaymentIntent, SignerGate
from wallet_privacy import Coin, Intent, Policy, select_coins


def local_private_network():
    return NetworkPlan(
        (
            Endpoint("chain_scan", "127.0.0.1", 8332, "local", False, True),
            Endpoint("tx_broadcast", "broadcast-hidden.onion", 8333, "tor", True),
        )
    )


def selection_single():
    return select_coins(
        [Coin(f"{1:064x}", 0, 100_000, "cluster-a", 10)],
        [Intent("receiver-payment", 50_000)],
        1_000,
    )


def original_single():
    return Transaction(
        version=2,
        locktime=0,
        inputs=(
            TxInput(f"{1:064x}", 0, 100_000, "sender"),
        ),
        outputs=(
            TxOutput("receiver-payment", 50_000, "receiver"),
            TxOutput("sender-change", 49_000, "sender"),
        ),
    )


def proposal_single(*, change=49_000, receiver_atoms=20_000, payment=69_000):
    return Transaction(
        version=2,
        locktime=0,
        inputs=(
            TxInput(f"{1:064x}", 0, 100_000, "sender"),
            TxInput(
                f"{9:064x}",
                0,
                receiver_atoms,
                "receiver",
                finalized=True,
                utxo_present=True,
            ),
        ),
        outputs=(
            TxOutput("receiver-payment", payment, "receiver"),
            TxOutput("sender-change", change, "sender"),
        ),
    )


def approval(*, merge=False, max_fee=1_000, payjoin=True, increase=True):
    return Approval(
        intents=(PaymentIntent("receiver-payment", 50_000),),
        max_fee_atoms=max_fee,
        allow_cluster_merge=merge,
        allow_payjoin=payjoin,
        allow_payment_increase=increase,
    )


def authorize(
    *,
    selection=None,
    original=None,
    proposal=None,
    context=None,
    provider=None,
    approve=None,
    network=None,
):
    provider = FixtureSigner() if provider is None else provider
    return provider, authorize_payjoin_stack(
        selection=selection_single() if selection is None else selection,
        original=original_single() if original is None else original,
        proposal=proposal_single() if proposal is None else proposal,
        payjoin_context=PayjoinContext(payment_output_index=0) if context is None else context,
        signer_gate=SignerGate(provider),
        approval=approval() if approve is None else approve,
        network_plan=local_private_network() if network is None else network,
        network_policy=NetworkPolicy(),
        request_id="aa" * 32,
        tx_digest="bb" * 32,
    )


class PrivacyStackIntegrationTests(unittest.TestCase):
    def test_full_normalized_payjoin_flow_passes(self):
        provider, evidence = authorize()
        self.assertEqual(evidence["result"], "PASS")
        self.assertTrue(evidence["signed"])
        self.assertEqual(provider.calls, 1)
        self.assertEqual(evidence["network"]["broadcast_route"], "tor")
        self.assertIn("PAYJOIN_PROPOSAL", evidence["signer"]["warning_codes"])

    def test_network_failure_occurs_before_signer(self):
        provider = FixtureSigner()
        direct = NetworkPlan(
            (
                Endpoint("chain_scan", "127.0.0.1", 8332, "local", False, True),
                Endpoint("tx_broadcast", "peer.example", 8333, "direct", True),
            )
        )
        with self.assertRaisesRegex(StackError, "^NETWORK_PRIVATE_BROADCAST_REQUIRED$"):
            authorize(provider=provider, network=direct)
        self.assertEqual(provider.calls, 0)

    def test_payjoin_must_be_explicitly_approved(self):
        provider = FixtureSigner()
        with self.assertRaisesRegex(StackError, "^SIGNER_PAYJOIN_NOT_APPROVED$"):
            authorize(
                provider=provider,
                approve=approval(payjoin=False, increase=False),
            )
        self.assertEqual(provider.calls, 0)

    def test_payment_increase_must_be_explicitly_approved(self):
        provider = FixtureSigner()
        with self.assertRaisesRegex(StackError, "^SIGNER_PAYMENT_INTENT_MISMATCH$"):
            authorize(
                provider=provider,
                approve=approval(payjoin=True, increase=False),
            )
        self.assertEqual(provider.calls, 0)

    def test_sender_debit_cap_survives_payjoin_composition(self):
        provider = FixtureSigner()
        proposal = proposal_single(change=48_500, receiver_atoms=20_000, payment=69_000)
        context = PayjoinContext(
            payment_output_index=0,
            fee_contribution_output_index=1,
            max_additional_fee_contribution=500,
        )
        with self.assertRaisesRegex(StackError, "^SIGNER_SENDER_DEBIT_EXCEEDED$"):
            authorize(
                provider=provider,
                proposal=proposal,
                context=context,
                approve=approval(max_fee=1_000),
            )
        self.assertEqual(provider.calls, 0)

    def test_wallet_input_binding_cannot_be_substituted(self):
        provider = FixtureSigner()
        original = Transaction(
            version=2,
            locktime=0,
            inputs=(TxInput(f"{7:064x}", 0, 100_000, "sender"),),
            outputs=original_single().outputs,
        )
        with self.assertRaisesRegex(StackError, "^WALLET_INPUT_BINDING_MISMATCH$"):
            authorize(provider=provider, original=original)
        self.assertEqual(provider.calls, 0)

    def test_cluster_merge_warning_reaches_signer_approval(self):
        selection = select_coins(
            [
                Coin(f"{1:064x}", 0, 30_000, "cluster-a", 10),
                Coin(f"{2:064x}", 0, 30_000, "cluster-b", 10),
            ],
            [Intent("receiver-payment", 50_000)],
            1_000,
            Policy(allow_cluster_merge=True),
        )
        original = Transaction(
            2,
            0,
            (
                TxInput(f"{1:064x}", 0, 30_000, "sender"),
                TxInput(f"{2:064x}", 0, 30_000, "sender"),
            ),
            (
                TxOutput("receiver-payment", 50_000, "receiver"),
                TxOutput("sender-change", 9_000, "sender"),
            ),
        )
        proposal = Transaction(
            2,
            0,
            (
                TxInput(f"{1:064x}", 0, 30_000, "sender"),
                TxInput(f"{9:064x}", 0, 20_000, "receiver", finalized=True),
                TxInput(f"{2:064x}", 0, 30_000, "sender"),
            ),
            (
                TxOutput("receiver-payment", 69_000, "receiver"),
                TxOutput("sender-change", 9_000, "sender"),
            ),
        )
        provider = FixtureSigner()
        with self.assertRaisesRegex(StackError, "^SIGNER_CLUSTER_MERGE_NOT_APPROVED$"):
            authorize(
                selection=selection,
                original=original,
                proposal=proposal,
                provider=provider,
                approve=approval(merge=False),
            )
        self.assertEqual(provider.calls, 0)

        provider, evidence = authorize(
            selection=selection,
            original=original,
            proposal=proposal,
            provider=FixtureSigner(),
            approve=approval(merge=True),
        )
        self.assertEqual(evidence["result"], "PASS")
        self.assertEqual(provider.calls, 1)

    def test_payjoin_mutation_is_stopped_before_signer(self):
        provider = FixtureSigner()
        bad = proposal_single(change=48_000, payment=70_000)
        with self.assertRaisesRegex(StackError, "^PAYJOIN_PROTECTED_OUTPUT_CHANGED$"):
            authorize(provider=provider, proposal=bad)
        self.assertEqual(provider.calls, 0)

    def test_stack_telemetry_contains_no_sensitive_identifiers_or_amounts(self):
        _, evidence = authorize()
        event = redacted_stack_event(evidence)
        rendered = repr(event)
        for value in (
            "receiver-payment",
            "sender-change",
            "broadcast-hidden.onion",
            f"{1:064x}",
            f"{9:064x}",
            "50000",
            "69000",
            "100000",
        ):
            self.assertNotIn(value, rendered)


if __name__ == "__main__":
    unittest.main()
