"""V2-04 research-only adapter: V2 capabilities AND existing V1 signer gate.

No signer implementation, key derivation, proof verification, RPC, broadcast or
Core state mutation lives here. The trusted local wallet supplies the exact
canonical V1 SignRequest, an independent V1 Approval and a trusted clock.
The authority and its issuance keys must NEVER be exposed to remote callers.
A V2 policy ALLOW alone cannot produce any signature.

Only qualified regtest/testnet environments. Not a production or mainnet API.
"""
from __future__ import annotations

from collections.abc import Mapping

from policy import PolicyAuthority
from signer_abstraction import Approval, SignRequest, SignerGate


class BridgeDenied(ValueError):
    """Constant-code local boundary rejection; do not log request contents."""


class LocalV1SignerBridge:
    """Narrow composition over frozen Phase 3/12 V1 signer interfaces.

    A capability is bound to the local wallet account, the canonical V1
    request_id and network. An entirely separate V1 Approval and SignerGate
    remain mandatory. Failures after policy authorization can consume a
    one-shot grant: fail closed and issue a fresh grant only from trusted UI.
    """

    def __init__(
        self, authority: PolicyAuthority, gate: SignerGate, *,
        account_scope: str
    ) -> None:
        if (not isinstance(authority, PolicyAuthority)
                or not isinstance(gate, SignerGate)
                or type(account_scope) is not str
                or not account_scope or len(account_scope) > 256
                or account_scope in ("*", "all")
                or gate.provider.capabilities.production is not False):
            raise BridgeDenied("BRIDGE_UNQUALIFIED")
        self._authority = authority
        self._gate = gate
        self._account_scope = account_scope

    def sign(
        self, capability_request: Mapping[str, object],
        sign_request: SignRequest, approval: Approval, *, now: int
    ):
        if (not isinstance(capability_request, Mapping)
                or not isinstance(sign_request, SignRequest)
                or not isinstance(approval, Approval)
                or type(now) is not int
                or not 0 <= now < (1 << 63)
                or sign_request.network not in ("regtest", "testnet")):
            raise BridgeDenied("BRIDGE_DENIED")
        try:
            sign_request.validate_shape()
            approval.validate()
        except ValueError:
            raise BridgeDenied("BRIDGE_DENIED") from None
        # Bind the V2 grant to the V1 canonical PSBT digest-based request_id.
        # Caller-supplied arbitrary request IDs are rejected by the frozen
        # Phase 12 WAM PSBT adapter, which is tested separately in this phase.
        if (capability_request.get("action") != "SIGN"
                or capability_request.get("actor_role") != "signer"
                or capability_request.get("network_id") != sign_request.network
                or capability_request.get("resource_scope") != sign_request.request_id
                or capability_request.get("account_scope") != self._account_scope):
            raise BridgeDenied("BRIDGE_DENIED")
        if self._authority.authorize(capability_request, now=now) != "ALLOW_POLICY_ONLY":
            raise BridgeDenied("BRIDGE_DENIED")
        # An independent V1 signer gate STILL verifies the payment intent,
        # fee, change ownership, replay and provider response. No fallback.
        return self._gate.sign(sign_request, approval)
