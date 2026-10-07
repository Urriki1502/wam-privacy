import sys
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from coincurve import PrivateKey
from real_adapters import (
    AdapterError,
    WspPsbtSignerProvider,
    core_v0_psbt,
    make_local_wam_rpc,
    request_id_from_psbt,
    sign_request_from_psbt,
)
from signer_abstraction import Approval, PaymentIntent, ProviderError, SignerGate
from wam_sp.psbt import PSBT, Tx


def key(n: int) -> PrivateKey:
    return PrivateKey(n.to_bytes(32, "big"))


def p2tr(k: PrivateKey) -> bytes:
    return b"\x51\x20" + k.public_key.format()[1:]


def fixture():
    input_key = key(7)
    payment_key = key(11)
    change_key = key(13)
    input_script = p2tr(input_key)
    payment_script = p2tr(payment_key)
    change_script = p2tr(change_key)
    tx = Tx(
        inputs=(("11" * 32, 0),),
        outputs=((90_000, payment_script), (9_000, change_script)),
    )
    psbt = PSBT(tx=tx, utxos=((100_000, input_script),), version=2)
    return psbt, input_key, payment_script, change_script


class Phase12RealAdapterTests(unittest.TestCase):
    def test_canonical_psbt_derives_signer_view_and_stable_request_id(self):
        psbt, _, payment, change = fixture()
        raw = psbt.encode()
        owned = frozenset({change})
        request = sign_request_from_psbt(raw, wallet_owned_output_scripts=owned)

        self.assertEqual(request.request_id, request_id_from_psbt(raw, network="regtest", wallet_owned_output_scripts=owned))
        self.assertEqual(request.tx_digest, psbt.txid())
        self.assertEqual(request.fee_atoms, 1_000)
        self.assertEqual(request.wallet_input_atoms, 100_000)
        self.assertEqual(request.outputs[0].destination, "script:" + payment.hex())
        self.assertEqual(request.outputs[0].role, "payment")
        self.assertEqual(request.outputs[1].role, "change")
        self.assertIn("CHANGE_CREATED", request.warning_codes)

    def test_request_id_cannot_be_rotated_by_caller(self):
        psbt, _, _, change = fixture()
        raw = psbt.encode()
        with self.assertRaisesRegex(AdapterError, "^REQUEST_ID_MISMATCH$"):
            sign_request_from_psbt(
                raw,
                request_id="aa" * 32,
                wallet_owned_output_scripts=frozenset({change}),
            )

    def test_mainnet_is_not_qualified(self):
        psbt, _, _, _ = fixture()
        with self.assertRaisesRegex(AdapterError, "^NETWORK_NOT_QUALIFIED$"):
            sign_request_from_psbt(psbt.encode(), network="mainnet")

    def test_real_schnorr_signing_passes_phase3_gate_and_exports_core_v0(self):
        psbt, input_key, payment, change = fixture()
        raw = psbt.encode()
        owned = frozenset({change})
        request = sign_request_from_psbt(raw, wallet_owned_output_scripts=owned)
        provider = WspPsbtSignerProvider(raw, (input_key,), wallet_owned_output_scripts=owned)
        approval = Approval(
            intents=(PaymentIntent("script:" + payment.hex(), 90_000),),
            max_fee_atoms=1_000,
        )

        result = SignerGate(provider).sign(request, approval)
        signed = PSBT.decode(result.envelope)
        self.assertEqual(signed.txid(), psbt.txid())
        self.assertTrue(signed.finalize())

        exported = core_v0_psbt(result.envelope)
        core_psbt = PSBT.from_base64(exported)
        self.assertEqual(core_psbt.version, 0)
        self.assertTrue(core_psbt.finalize())

    def test_mutated_signer_view_is_rejected_before_crypto(self):
        psbt, input_key, _, change = fixture()
        raw = psbt.encode()
        owned = frozenset({change})
        request = sign_request_from_psbt(raw, wallet_owned_output_scripts=owned)
        provider = WspPsbtSignerProvider(raw, (input_key,), wallet_owned_output_scripts=owned)

        with self.assertRaisesRegex(AdapterError, "^SIGN_REQUEST_MISMATCH$"):
            provider.sign(replace(request, fee_atoms=request.fee_atoms + 1))

    def test_already_signed_psbt_cannot_be_reinterpreted_as_new_request(self):
        psbt, input_key, _, _ = fixture()
        signed = psbt.sign([input_key])
        with self.assertRaisesRegex(AdapterError, "^PSBT_ALREADY_SIGNED$"):
            sign_request_from_psbt(signed.encode())

    def test_unsigned_psbt_cannot_be_exported_as_core_final(self):
        psbt, _, _, _ = fixture()
        with self.assertRaisesRegex(AdapterError, "^CORE_EXPORT_FAILED$"):
            core_v0_psbt(psbt.encode())

    def test_rpc_boundary_is_loopback_only(self):
        with tempfile.TemporaryDirectory() as d:
            cookie = Path(d) / ".cookie"
            rpc = make_local_wam_rpc("http://127.0.0.1:18443", cookie)
            self.assertEqual(rpc.url, "http://127.0.0.1:18443")
            with self.assertRaisesRegex(AdapterError, "^RPC_ENDPOINT_REJECTED$"):
                make_local_wam_rpc("http://localhost:18443", cookie)
            with self.assertRaisesRegex(AdapterError, "^RPC_ENDPOINT_REJECTED$"):
                make_local_wam_rpc("http://192.0.2.1:18443", cookie)


if __name__ == "__main__":
    unittest.main()
