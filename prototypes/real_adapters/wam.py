"""Real WAM/WSP adapter boundary for Phase 12.

Unlike the earlier Phase 3/6 fixture path, this module parses the pinned
wam-silent-payments PSBT implementation and delegates cryptographic signing to
its real P2TR/Schnorr signing code.

The adapter remains regtest/testnet research infrastructure. It never opens a
remote RPC endpoint: WSP's RPC class accepts canonical IPv4 loopback only and
attests regtest before mutation.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from signer_abstraction import SignedResult, SignRequest, SignerCapabilities
from wam_sp.adapters.sp_psbt import core_v0_export
from wam_sp.psbt import PSBT
from wam_sp.rpc import Cookie, RPC


class AdapterError(ValueError):
    """Fixed-code failure at the real WAM adapter boundary."""


def _fail(code: str) -> None:
    raise AdapterError(code)


def _decode(raw: bytes) -> PSBT:
    if not isinstance(raw, bytes):
        _fail("PSBT_TYPE")
    try:
        psbt = PSBT.decode(raw)
        if psbt.encode() != raw:
            _fail("PSBT_NONCANONICAL")
        return psbt
    except AdapterError:
        raise
    except Exception:
        _fail("PSBT_INVALID")


def _fee(psbt: PSBT) -> int:
    total_in = sum(value for value, _ in psbt.utxos)
    total_out = sum(value for value, _ in psbt.tx.outputs)
    fee = total_in - total_out
    if not 0 <= fee <= 1_000_000:
        _fail("FEE_RANGE")
    return fee


def _destination(script: bytes) -> str:
    if not isinstance(script, bytes) or not 1 <= len(script) <= 10_000:
        _fail("SCRIPT_SHAPE")
    return "script:" + script.hex()


def _owned_scripts(value: frozenset[bytes]) -> tuple[bytes, ...]:
    if not isinstance(value, frozenset):
        _fail("OWNERSHIP_SET_TYPE")
    scripts = tuple(sorted(value))
    for script in scripts:
        if not isinstance(script, bytes) or not 1 <= len(script) <= 10_000:
            _fail("OWNERSHIP_SCRIPT")
    return scripts


def request_id_from_psbt(
    raw: bytes,
    *,
    network: str,
    wallet_owned_output_scripts: frozenset[bytes] = frozenset(),
) -> str:
    """Derive the replay identifier from canonical transaction material.

    Ownership classification is included because it affects the signer-visible
    payment/change split. Callers cannot rotate an arbitrary request id to evade
    the Phase 3 completed-request replay gate.
    """

    _decode(raw)
    if network not in ("regtest", "testnet"):
        _fail("NETWORK_NOT_QUALIFIED")
    owned = _owned_scripts(wallet_owned_output_scripts)

    h = sha256()
    h.update(b"WAM/Privacy/Phase12/SignRequest/v1\x00")
    h.update(network.encode("ascii") + b"\x00")
    h.update(len(raw).to_bytes(4, "little"))
    h.update(raw)
    for script in owned:
        h.update(len(script).to_bytes(2, "little"))
        h.update(script)
    return h.hexdigest()


def sign_request_from_psbt(
    raw: bytes,
    *,
    request_id: str | None = None,
    wallet_owned_output_scripts: frozenset[bytes] = frozenset(),
    network: str = "regtest",
    warning_codes: tuple[str, ...] = (),
) -> SignRequest:
    """Derive the signer view from canonical WSP PSBT bytes, not caller claims."""

    psbt = _decode(raw)
    if any(psbt.signatures):
        _fail("PSBT_ALREADY_SIGNED")
    if network not in ("regtest", "testnet"):
        _fail("NETWORK_NOT_QUALIFIED")

    owned_scripts = _owned_scripts(wallet_owned_output_scripts)
    derived_id = request_id_from_psbt(
        raw,
        network=network,
        wallet_owned_output_scripts=wallet_owned_output_scripts,
    )
    if request_id is not None and request_id != derived_id:
        _fail("REQUEST_ID_MISMATCH")

    owned = set(owned_scripts)
    change_count = 0
    outputs = []
    from signer_abstraction import TransactionOutput

    for value, script in psbt.tx.outputs:
        is_change = script in owned
        if is_change:
            change_count += 1
        outputs.append(
            TransactionOutput(
                destination=_destination(script),
                atoms=value,
                role="change" if is_change else "payment",
                wallet_owned=is_change,
            )
        )
    if change_count > 1:
        _fail("MULTIPLE_CHANGE_OUTPUTS")

    warnings = list(warning_codes)
    if change_count and "CHANGE_CREATED" not in warnings:
        warnings.append("CHANGE_CREATED")

    request = SignRequest(
        request_id=derived_id,
        network=network,
        tx_digest=psbt.txid(),
        input_count=len(psbt.tx.inputs),
        outputs=tuple(outputs),
        fee_atoms=_fee(psbt),
        wallet_input_atoms=sum(value for value, _ in psbt.utxos),
        warning_codes=tuple(warnings),
    )
    try:
        request.validate_shape()
    except ValueError as exc:
        raise AdapterError(str(exc)) from None
    return request


class WspPsbtSignerProvider:
    """Real cryptographic WSP PSBT signer behind the Phase 3 provider interface."""

    def __init__(
        self,
        psbt: bytes,
        keys: tuple[object | None, ...],
        *,
        wallet_owned_output_scripts: frozenset[bytes] = frozenset(),
    ):
        self._psbt = bytes(psbt)
        self._keys = tuple(keys)
        self._owned = frozenset(wallet_owned_output_scripts)
        parsed = _decode(self._psbt)
        _owned_scripts(self._owned)
        if len(self._keys) != len(parsed.tx.inputs):
            _fail("KEY_COUNT")

    @property
    def capabilities(self) -> SignerCapabilities:
        return SignerCapabilities(
            kind="software",
            supports_networks=("regtest", "testnet"),
            production=False,
        )

    def sign(self, request: SignRequest) -> SignedResult:
        expected = sign_request_from_psbt(
            self._psbt,
            request_id=request.request_id,
            wallet_owned_output_scripts=self._owned,
            network=request.network,
            warning_codes=request.warning_codes,
        )
        if expected != request:
            _fail("SIGN_REQUEST_MISMATCH")

        try:
            signed = _decode(self._psbt).sign(list(self._keys))
            signed.finalize()
        except Exception:
            _fail("CRYPTO_SIGNING_FAILED")

        return SignedResult(
            request_id=request.request_id,
            tx_digest=request.tx_digest,
            envelope=signed.encode(),
        )


def core_v0_psbt(signed_psbt: bytes) -> str:
    """Return the WAM Core v0-compatible PSBT after verified finalization."""

    psbt = _decode(signed_psbt)
    try:
        psbt.finalize()
        return core_v0_export(psbt).base64()
    except Exception:
        _fail("CORE_EXPORT_FAILED")


def make_local_wam_rpc(
    url: str,
    cookie_path: str | Path,
    *,
    allow_broadcast: bool = False,
) -> RPC:
    """Construct the qualified WSP RPC boundary (loopback-only, regtest-attested)."""

    try:
        return RPC(
            url,
            Cookie(Path(cookie_path)),
            allow_broadcast=allow_broadcast,
        )
    except Exception:
        _fail("RPC_ENDPOINT_REJECTED")
