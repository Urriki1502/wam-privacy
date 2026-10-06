import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from signer_abstraction import (
    Approval,
    FixtureSigner,
    PaymentIntent,
    ProviderError,
    SignRequest,
    SignerGate,
    SignerPolicy,
    TransactionOutput,
    redacted_signer_event,
)


def request(
    *,
    request_id="11" * 32,
    network="regtest",
    digest="22" * 32,
    fee=1_000,
    inputs=1,
    payment=("wamrt-recipient", 50_000),
    change=None,
    wallet_input=None,
    warnings=(),
):
    outputs = [TransactionOutput(payment[0], payment[1], "payment", False)]
    if change is not None:
        outputs.append(TransactionOutput(change[0], change[1], "change", True))
    return SignRequest(
        request_id=request_id,
        network=network,
        tx_digest=digest,
        input_count=inputs,
        outputs=tuple(outputs),
        fee_atoms=fee,
        wallet_input_atoms=wallet_input,
        warning_codes=tuple(warnings),
    )


def approval(
    *,
    fee=1_000,
    merge=False,
    payjoin=False,
    payment_increase=False,
    payment=("wamrt-recipient", 50_000),
):
    return Approval(
        intents=(PaymentIntent(payment[0], payment[1]),),
        max_fee_atoms=fee,
        allow_cluster_merge=merge,
        allow_payjoin=payjoin,
        allow_payment_increase=payment_increase,
    )


class SignerAbstractionTests(unittest.TestCase):
    def test_valid_regtest_request_reaches_provider(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        result = gate.sign(request(), approval())
        self.assertEqual(provider.calls, 1)
        self.assertEqual(result.request_id, "11" * 32)
        self.assertFalse(provider.capabilities.production)

    def test_network_policy_rejects_before_provider(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        with self.assertRaisesRegex(ProviderError, "^NETWORK_NOT_ALLOWED$"):
            gate.sign(request(network="mainnet"), approval())
        self.assertEqual(provider.calls, 0)

    def test_payment_mismatch_rejects_before_provider(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        with self.assertRaisesRegex(ProviderError, "^PAYMENT_INTENT_MISMATCH$"):
            gate.sign(request(payment=("evil", 50_000)), approval())
        self.assertEqual(provider.calls, 0)

    def test_fee_above_approval_rejects_before_provider(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        with self.assertRaisesRegex(ProviderError, "^FEE_NOT_APPROVED$"):
            gate.sign(request(fee=2_000), approval(fee=1_000))
        self.assertEqual(provider.calls, 0)

    def test_cluster_merge_requires_explicit_approval(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        with self.assertRaisesRegex(ProviderError, "^CLUSTER_MERGE_NOT_APPROVED$"):
            gate.sign(
                request(warnings=("CLUSTER_MERGE",)),
                approval(merge=False),
            )
        self.assertEqual(provider.calls, 0)

        ok = gate.sign(
            request(request_id="12" * 32, warnings=("CLUSTER_MERGE",)),
            approval(merge=True),
        )
        self.assertEqual(ok.request_id, "12" * 32)
        self.assertEqual(provider.calls, 1)

    def test_change_warning_must_match_transaction_view(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        with self.assertRaisesRegex(ProviderError, "^CHANGE_WARNING_MISMATCH$"):
            gate.sign(
                request(change=("wallet-change", 10_000), warnings=()),
                approval(),
            )

    def test_unverified_change_fails_shape_validation(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        bad = SignRequest(
            request_id="13" * 32,
            network="regtest",
            tx_digest="22" * 32,
            input_count=1,
            outputs=(
                TransactionOutput("wamrt-recipient", 50_000, "payment", False),
                TransactionOutput("not-verified-change", 10_000, "change", False),
            ),
            fee_atoms=1_000,
            warning_codes=("CHANGE_CREATED",),
        )
        with self.assertRaisesRegex(ProviderError, "^UNVERIFIED_CHANGE$"):
            gate.sign(bad, approval())
        self.assertEqual(provider.calls, 0)

    def test_unknown_warning_fails_closed(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        with self.assertRaisesRegex(ProviderError, "^UNKNOWN_WARNING$"):
            gate.sign(request(warnings=("MAGIC_PRIVACY",)), approval())
        self.assertEqual(provider.calls, 0)

    def test_successful_request_cannot_be_replayed_in_session(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        req = request()
        gate.sign(req, approval())
        with self.assertRaisesRegex(ProviderError, "^REQUEST_REPLAY$"):
            gate.sign(req, approval())
        self.assertEqual(provider.calls, 1)

    def test_provider_failure_does_not_consume_request(self):
        provider = FixtureSigner(fail=True)
        gate = SignerGate(provider)
        req = request()
        with self.assertRaisesRegex(ProviderError, "^PROVIDER_FAILED$"):
            gate.sign(req, approval())
        self.assertEqual(provider.calls, 1)

        provider.fail = False
        result = gate.sign(req, approval())
        self.assertEqual(result.request_id, req.request_id)
        self.assertEqual(provider.calls, 2)

    def test_mismatched_provider_result_is_not_accepted(self):
        provider = FixtureSigner(mismatch=True)
        gate = SignerGate(provider)
        req = request()
        with self.assertRaisesRegex(ProviderError, "^PROVIDER_RESULT_MISMATCH$"):
            gate.sign(req, approval())
        provider.mismatch = False
        result = gate.sign(req, approval())
        self.assertEqual(result.tx_digest, req.tx_digest)

    def test_hard_policy_cap_is_independent_of_user_approval(self):
        provider = FixtureSigner()
        gate = SignerGate(provider, SignerPolicy(hard_max_fee_atoms=500))
        with self.assertRaisesRegex(ProviderError, "^FEE_NOT_APPROVED$"):
            gate.sign(request(fee=600), approval(fee=1_000))

    def test_redacted_event_contains_no_payment_identifiers_or_amounts(self):
        provider = FixtureSigner()
        req = request(
            payment=("sensitive-recipient", 54_321),
            change=("sensitive-change", 12_345),
            warnings=("CHANGE_CREATED",),
        )
        event = redacted_signer_event(req, provider, "PASS")
        rendered = repr(event)
        for secret in (
            "sensitive-recipient",
            "sensitive-change",
            req.request_id,
            req.tx_digest,
            "54321",
            "12345",
        ):
            self.assertNotIn(secret, rendered)


    def test_payjoin_requires_explicit_approval(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        req = request(
            fee=2_000,
            payment=("wamrt-recipient", 69_000),
            change=("wallet-change", 49_000),
            wallet_input=100_000,
            warnings=("CHANGE_CREATED", "PAYJOIN_PROPOSAL"),
        )
        with self.assertRaisesRegex(ProviderError, "^PAYJOIN_NOT_APPROVED$"):
            gate.sign(req, approval())
        self.assertEqual(provider.calls, 0)

    def test_payjoin_receiver_funded_payment_increase_can_be_approved(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        req = request(
            fee=2_000,
            payment=("wamrt-recipient", 69_000),
            change=("wallet-change", 49_000),
            wallet_input=100_000,
            warnings=("CHANGE_CREATED", "PAYJOIN_PROPOSAL"),
        )
        result = gate.sign(
            req,
            approval(payjoin=True, payment_increase=True, fee=1_000),
        )
        self.assertEqual(result.request_id, req.request_id)
        self.assertEqual(provider.calls, 1)

    def test_payjoin_payment_increase_without_flag_fails(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        req = request(
            fee=2_000,
            payment=("wamrt-recipient", 69_000),
            change=("wallet-change", 49_000),
            wallet_input=100_000,
            warnings=("CHANGE_CREATED", "PAYJOIN_PROPOSAL"),
        )
        with self.assertRaisesRegex(ProviderError, "^PAYMENT_INTENT_MISMATCH$"):
            gate.sign(req, approval(payjoin=True))
        self.assertEqual(provider.calls, 0)

    def test_payjoin_sender_debit_cannot_exceed_approved_intent_plus_fee(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        req = request(
            fee=2_500,
            payment=("wamrt-recipient", 69_000),
            change=("wallet-change", 48_500),
            wallet_input=100_000,
            warnings=("CHANGE_CREATED", "PAYJOIN_PROPOSAL"),
        )
        with self.assertRaisesRegex(ProviderError, "^SENDER_DEBIT_EXCEEDED$"):
            gate.sign(
                req,
                approval(payjoin=True, payment_increase=True, fee=1_000),
            )
        self.assertEqual(provider.calls, 0)

    def test_payjoin_requires_known_wallet_input_amount(self):
        provider = FixtureSigner()
        gate = SignerGate(provider)
        req = request(
            fee=2_000,
            payment=("wamrt-recipient", 69_000),
            change=("wallet-change", 49_000),
            warnings=("CHANGE_CREATED", "PAYJOIN_PROPOSAL"),
        )
        with self.assertRaisesRegex(ProviderError, "^SENDER_DEBIT_UNKNOWN$"):
            gate.sign(
                req,
                approval(payjoin=True, payment_increase=True, fee=1_000),
            )
        self.assertEqual(provider.calls, 0)

    def test_model_exposes_no_private_key_or_seed_field(self):
        names = set(SignRequest.__dataclass_fields__)
        self.assertFalse(names & {"seed", "private_key", "spend_secret", "mnemonic"})


if __name__ == "__main__":
    unittest.main()
