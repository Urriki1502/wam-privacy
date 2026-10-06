"""Signer-provider boundary and validation gate.

The gate validates policy before a provider is called. The fixture provider does
not perform cryptographic signing and must never be treated as a WAM signature.
"""

from __future__ import annotations

from collections import Counter
from typing import Protocol, runtime_checkable

from .model import Approval, SignedResult, SignRequest, SignerCapabilities, SignerPolicy


class ProviderError(ValueError):
    """Fixed-code signer boundary failure."""


@runtime_checkable
class SigningProvider(Protocol):
    @property
    def capabilities(self) -> SignerCapabilities:
        ...

    def sign(self, request: SignRequest) -> SignedResult:
        ...


KNOWN_WARNINGS = {
    "CHANGE_CREATED",
    "CLUSTER_MERGE",
}


def _payments(request: SignRequest) -> Counter[tuple[str, int]]:
    return Counter(
        (o.destination, o.atoms)
        for o in request.outputs
        if o.role == "payment"
    )


def _approved(approval: Approval) -> Counter[tuple[str, int]]:
    return Counter((i.destination, i.atoms) for i in approval.intents)


def _validate_request(
    request: SignRequest,
    approval: Approval,
    policy: SignerPolicy,
    capabilities: SignerCapabilities,
) -> None:
    try:
        request.validate_shape()
        approval.validate()
        policy.validate()
        capabilities.validate()
    except ValueError as exc:
        raise ProviderError(str(exc)) from None

    if request.network not in policy.allowed_networks:
        raise ProviderError("NETWORK_NOT_ALLOWED")
    if request.network not in capabilities.supports_networks:
        raise ProviderError("PROVIDER_NETWORK_UNSUPPORTED")
    if request.input_count > policy.max_inputs:
        raise ProviderError("INPUT_POLICY")
    if len(request.outputs) > policy.max_outputs:
        raise ProviderError("OUTPUT_POLICY")
    if request.fee_atoms > min(approval.max_fee_atoms, policy.hard_max_fee_atoms):
        raise ProviderError("FEE_NOT_APPROVED")

    unknown = set(request.warning_codes) - KNOWN_WARNINGS
    if unknown:
        raise ProviderError("UNKNOWN_WARNING")
    if "CLUSTER_MERGE" in request.warning_codes and not approval.allow_cluster_merge:
        raise ProviderError("CLUSTER_MERGE_NOT_APPROVED")

    change_outputs = [o for o in request.outputs if o.role == "change"]
    if len(change_outputs) > 1:
        raise ProviderError("MULTIPLE_CHANGE_OUTPUTS")
    if bool(change_outputs) != ("CHANGE_CREATED" in request.warning_codes):
        raise ProviderError("CHANGE_WARNING_MISMATCH")

    if _payments(request) != _approved(approval):
        raise ProviderError("PAYMENT_INTENT_MISMATCH")


class SignerGate:
    """One-session signing coordinator with post-success replay protection."""

    def __init__(self, provider: SigningProvider, policy: SignerPolicy | None = None):
        if not isinstance(provider, SigningProvider):
            raise ProviderError("INVALID_PROVIDER")
        self.provider = provider
        self.policy = SignerPolicy() if policy is None else policy
        self._completed: set[str] = set()

    def sign(self, request: SignRequest, approval: Approval) -> SignedResult:
        if request.request_id in self._completed:
            raise ProviderError("REQUEST_REPLAY")

        _validate_request(request, approval, self.policy, self.provider.capabilities)

        try:
            result = self.provider.sign(request)
        except Exception as exc:
            # Provider failures are retryable because the request has not been
            # marked completed. Do not leak provider exception details.
            raise ProviderError("PROVIDER_FAILED") from None

        if not isinstance(result, SignedResult):
            raise ProviderError("PROVIDER_RESULT_TYPE")
        if result.request_id != request.request_id or result.tx_digest != request.tx_digest:
            raise ProviderError("PROVIDER_RESULT_MISMATCH")
        if not isinstance(result.envelope, bytes) or not result.envelope:
            raise ProviderError("PROVIDER_RESULT_EMPTY")

        self._completed.add(request.request_id)
        return result


class FixtureSigner:
    """Non-cryptographic fixture for interface tests only."""

    def __init__(self, fail: bool = False, mismatch: bool = False):
        self.fail = fail
        self.mismatch = mismatch
        self.calls = 0

    @property
    def capabilities(self) -> SignerCapabilities:
        return SignerCapabilities(
            kind="fixture",
            supports_networks=("regtest",),
            production=False,
        )

    def sign(self, request: SignRequest) -> SignedResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("fixture failure")
        digest = ("00" * 32) if self.mismatch else request.tx_digest
        return SignedResult(
            request_id=request.request_id,
            tx_digest=digest,
            envelope=b"WAM-PRIVACY-TEST-FIXTURE:" + bytes.fromhex(request.tx_digest)[:8],
        )


def redacted_signer_event(
    request: SignRequest,
    provider: SigningProvider,
    result: str,
) -> dict:
    """Minimal signer telemetry without payment identifiers or exact amounts."""

    return {
        "schema": 1,
        "provider_kind": provider.capabilities.kind,
        "network": request.network,
        "input_count": request.input_count,
        "output_count": len(request.outputs),
        "warning_codes": list(request.warning_codes),
        "result": result,
    }
