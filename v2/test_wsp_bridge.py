"""V2-04: V2 capability -> frozen V1 WSP PSBT/Schnorr signer on regtest.

Pinned WSP dependency is installed ONLY in isolated CI; tests never broadcast,
connect to a daemon, use live funds or touch a public network.
"""
from dataclasses import asdict, replace
from unittest.mock import patch
import unittest

from coincurve import PrivateKey
from wam_sp.psbt import PSBT, Tx

from bridge import BridgeDenied, LocalV1SignerBridge
from policy import Grant, PolicyAuthority
from real_adapters import (
    AdapterError, WspPsbtSignerProvider, core_v0_psbt,
    sign_request_from_psbt,
)
from signer_abstraction import Approval, PaymentIntent, ProviderError, SignerGate


def p2tr(key: PrivateKey) -> bytes:
    return b"\x51\x20" + key.public_key.format()[1:]


class WspV2BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.input_key = PrivateKey((7).to_bytes(32, "big"))
        self.destination = p2tr(PrivateKey((11).to_bytes(32, "big")))
        self.change = p2tr(PrivateKey((13).to_bytes(32, "big")))
        self.psbt = PSBT(
            tx=Tx(
                inputs=(("11" * 32, 0),),
                outputs=((90_000, self.destination), (9_000, self.change)),
            ),
            utxos=((100_000, p2tr(self.input_key)),),
            version=2,
        )
        self.raw = self.psbt.encode()
        self.owned = frozenset({self.change})
        self.sign_request = sign_request_from_psbt(
            self.raw, network="regtest",
            wallet_owned_output_scripts=self.owned,
        )
        self.approval = Approval(
            intents=(PaymentIntent("script:" + self.destination.hex(), 90_000),),
            max_fee_atoms=1_000,
        )
        self.authority = PolicyAuthority(b"G" * 32, b"C" * 32)
        self.grant = Grant(
            "real-v1-sign", "signer", "SIGN", "wallet-a",
            self.sign_request.request_id, "regtest", "payment",
            1000, "session-a", single_use=True,
        )
        self.authority.issue_local_grant(self.grant)
        self.cap_req = {k: v for k, v in asdict(self.grant).items()
                        if k != "single_use"}
        self.provider = WspPsbtSignerProvider(
            self.raw, (self.input_key,),
            wallet_owned_output_scripts=self.owned,
        )
        self.bridge = LocalV1SignerBridge(
            self.authority, SignerGate(self.provider), account_scope="wallet-a"
        )

    def test_authenticated_v2_scope_and_independent_approval_sign_real_psbt(self):
        result = self.bridge.sign(
            self.cap_req, self.sign_request, self.approval, now=100
        )
        signed = PSBT.decode(result.envelope)
        self.assertEqual(signed.txid(), self.psbt.txid())
        self.assertTrue(signed.finalize())
        self.assertEqual(PSBT.from_base64(core_v0_psbt(result.envelope)).version, 0)

    def test_cross_scope_and_forged_capability_never_reach_cryptographic_provider(self):
        with patch.object(self.provider, "sign", wraps=self.provider.sign) as sign:
            for req in (
                {**self.cap_req, "resource_scope": "00" * 32},
                {**self.cap_req, "account_scope": "wallet-other"},
                {**self.cap_req, "actor_role": "scanner", "action": "SCAN"},
                {**self.cap_req, "network_id": "testnet"},
                {**self.cap_req, "capability_id": "unissued"},
            ):
                with self.subTest(req=req["capability_id"]):
                    with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
                        self.bridge.sign(req, self.sign_request, self.approval, now=100)
            sign.assert_not_called()

    def test_payment_mismatch_blocks_crypto_even_with_valid_capability(self):
        evil = Approval((PaymentIntent("script:" + self.change.hex(), 90_000),), 1000)
        with patch.object(self.provider, "sign", wraps=self.provider.sign) as sign:
            with self.assertRaisesRegex(ProviderError, "^PAYMENT_INTENT_MISMATCH$"):
                self.bridge.sign(self.cap_req, self.sign_request, evil, now=100)
            sign.assert_not_called()

    def test_caller_cannot_override_canonical_request_identifier(self):
        with self.assertRaisesRegex(AdapterError, "^REQUEST_ID_MISMATCH$"):
            sign_request_from_psbt(
                self.raw, network="regtest", request_id="ff" * 32,
                wallet_owned_output_scripts=self.owned,
            )
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(self.cap_req,
                             replace(self.sign_request, request_id="ff" * 32),
                             self.approval, now=100)

    def test_live_mainnet_and_malformed_psbt_never_qualified(self):
        with self.assertRaisesRegex(AdapterError, "^NETWORK_NOT_QUALIFIED$"):
            sign_request_from_psbt(self.raw, network="mainnet")
        with self.assertRaisesRegex(AdapterError, "^PSBT_INVALID$"):
            sign_request_from_psbt(b"not a psbt")
        with self.assertRaisesRegex(BridgeDenied, "^BRIDGE_DENIED$"):
            self.bridge.sign(
                self.cap_req,
                replace(self.sign_request, network="mainnet"),
                self.approval, now=100,
            )


if __name__ == "__main__":
    unittest.main()
