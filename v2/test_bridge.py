"""V2-04 negative and positive composition tests using frozen V1 SignerGate.

FixtureSigner is NOT cryptography. Real WSP PSBT signing is tested by the
separate pinned-WSP v2/test_wsp_bridge.py CI job.
"""
from dataclasses import asdict, replace
import unittest

from bridge import BridgeDenied, LocalV1SignerBridge
from policy import Grant, PolicyAuthority
from signer_abstraction import (
    Approval, FixtureSigner, PaymentIntent, ProviderError, SignRequest,
    SignerCapabilities, SignerGate, TransactionOutput,
)

GRANT_KEY = b"G" * 32
CONSENT_KEY = b"C" * 32


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.authority = PolicyAuthority(GRANT_KEY, CONSENT_KEY)
        self.provider = FixtureSigner()
        self.gate = SignerGate(self.provider)
        self.bridge = LocalV1SignerBridge(
            self.authority, self.gate, account_scope="wallet-a"
        )
        self.sign_request = SignRequest(
            request_id="01" * 32, network="regtest", tx_digest="02" * 32,
            input_count=1,
            outputs=(TransactionOutput("recipient-a", 40_000, "payment", False),),
            fee_atoms=1_000,
        )
        self.approval = Approval((PaymentIntent("recipient-a", 40_000),), 1_000)

    def provision(self, *, cap="sign-a", single_use=True):
        grant = Grant(
            cap, "signer", "SIGN", "wallet-a", self.sign_request.request_id,
            "regtest", "user-payment", 1000, "session-a",
            single_use=single_use,
        )
        self.authority.issue_local_grant(grant)
        return {k: v for k, v in asdict(grant).items() if k != "single_use"}

    def test_valid_local_signer_requires_both_independent_gates(self):
        req = self.provision()
        result = self.bridge.sign(req, self.sign_request, self.approval, now=100)
        self.assertEqual(result.request_id, self.sign_request.request_id)
        self.assertEqual(self.provider.calls, 1)
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(req, self.sign_request, self.approval, now=101)
        self.assertEqual(self.provider.calls, 1)

    def test_no_capability_cannot_reach_v1_signer(self):
        grant = Grant("missing", "signer", "SIGN", "wallet-a",
                      self.sign_request.request_id, "regtest",
                      "user-payment", 1000, "session-a")
        req = {k: v for k, v in asdict(grant).items() if k != "single_use"}
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(req, self.sign_request, self.approval, now=100)
        self.assertEqual(self.provider.calls, 0)

    def test_wrong_account_resource_network_role_action_deny_before_v1(self):
        req = self.provision()
        for patch in (
            {"account_scope": "wallet-b"},
            {"resource_scope": "ff" * 32},
            {"network_id": "testnet"},
            {"actor_role": "viewer", "action": "VIEW"},
            {"actor_role": "scanner", "action": "SCAN"},
            {"actor_role": "auditor", "action": "AUDIT"},
            {"actor_role": "discloser", "action": "DISCLOSE"},
        ):
            with self.subTest(patch=patch):
                with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
                    self.bridge.sign({**req, **patch}, self.sign_request,
                                     self.approval, now=100)
        self.assertEqual(self.provider.calls, 0)

    def test_cannot_rotate_v1_request_id_with_same_capability(self):
        req = self.provision()
        rotated = replace(self.sign_request, request_id="ff" * 32)
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(req, rotated, self.approval, now=100)
        self.assertEqual(self.provider.calls, 0)

    def test_mainnet_and_cross_network_qualified_fail_closed(self):
        req = self.provision()
        for network in ("mainnet", "testnet"):
            with self.subTest(network=network):
                with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
                    self.bridge.sign(req, replace(self.sign_request, network=network),
                                     self.approval, now=100)
        self.assertEqual(self.provider.calls, 0)

    def test_expired_revoked_and_restored_revocation_deny(self):
        req = self.provision(single_use=False)
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(req, self.sign_request, self.approval, now=1000)
        self.authority.revoke("sign-a")
        restored = PolicyAuthority.restore(
            self.authority.snapshot(), GRANT_KEY, CONSENT_KEY
        )
        rebuilt = LocalV1SignerBridge(restored, self.gate, account_scope="wallet-a")
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            rebuilt.sign(req, self.sign_request, self.approval, now=1001)
        self.assertEqual(self.provider.calls, 0)

    def test_single_use_grant_consumption_persists_across_restart(self):
        req = self.provision()
        self.bridge.sign(req, self.sign_request, self.approval, now=100)
        restored = PolicyAuthority.restore(
            self.authority.snapshot(), GRANT_KEY, CONSENT_KEY
        )
        rebuilt = LocalV1SignerBridge(restored, self.gate, account_scope="wallet-a")
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            rebuilt.sign(req, self.sign_request, self.approval, now=101)
        self.assertEqual(self.provider.calls, 1)

    def test_policy_only_allow_does_not_replace_v1_payment_approval(self):
        req = self.provision()
        bad = Approval((PaymentIntent("unapproved-recipient", 40_000),), 1_000)
        with self.assertRaisesRegex(ProviderError, "^PAYMENT_INTENT_MISMATCH$"):
            self.bridge.sign(req, self.sign_request, bad, now=100)
        self.assertEqual(self.provider.calls, 0)
        # One-shot grant is intentionally spent on downstream failure.
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(req, self.sign_request, self.approval, now=101)

    def test_v1_fee_gate_remains_authoritative(self):
        req = self.provision()
        bad = Approval((PaymentIntent("recipient-a", 40_000),), 500)
        with self.assertRaisesRegex(ProviderError, "^FEE_NOT_APPROVED$"):
            self.bridge.sign(req, self.sign_request, bad, now=100)
        self.assertEqual(self.provider.calls, 0)

    def test_v1_replay_gate_blocks_reuse_even_with_multiuse_v2_capability(self):
        req = self.provision(single_use=False)
        self.bridge.sign(req, self.sign_request, self.approval, now=100)
        with self.assertRaisesRegex(ProviderError, "^REQUEST_REPLAY$"):
            self.bridge.sign(req, self.sign_request, self.approval, now=101)
        self.assertEqual(self.provider.calls, 1)

    def test_malformed_shape_extra_fields_and_clock_regression(self):
        req = self.provision(single_use=False)
        for malformed in ({**req, "seed": "sensitive"}, {**req, "policy_version": 3}):
            with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
                self.bridge.sign(malformed, self.sign_request, self.approval, now=500)
        self.assertEqual(self.authority.authorize(req, now=500), "ALLOW_POLICY_ONLY")
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(req, self.sign_request, self.approval, now=499)
        self.assertEqual(self.provider.calls, 0)

    def test_unknown_or_invalid_approval_never_reaches_signer(self):
        req = self.provision()
        for approval in (None, object(), Approval((), 1000)):
            with self.subTest(approval=type(approval).__name__):
                with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
                    self.bridge.sign(req, self.sign_request, approval, now=100)
        self.assertEqual(self.provider.calls, 0)

    def test_no_production_signer_or_wildcard_account(self):
        class ProductionFixture(FixtureSigner):
            @property
            def capabilities(self):
                return SignerCapabilities(
                    kind="software", supports_networks=("regtest",),
                    production=True,
                )

        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_UNQUALIFIED$"):
            LocalV1SignerBridge(
                self.authority, SignerGate(ProductionFixture()),
                account_scope="wallet-a",
            )
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_UNQUALIFIED$"):
            LocalV1SignerBridge(
                self.authority, self.gate, account_scope="*",
            )


if __name__ == "__main__":
    unittest.main()
