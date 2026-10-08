"""V2-03: pure, offline routing-policy / network-observer simulator.

NO sockets, HTTP, RPC, wallet signing, live relays or chain validation.
A simulator route decision is not evidence of privacy or network anonymity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

MAX_ENDPOINTS = 16
MAX_ID = 128
MAX_TIMESTAMP = (1 << 63) - 1

TRANSPORT_PRIORITY = ("TOR", "I2P", "DIRECT")
NETWORKS = frozenset(("regtest", "testnet", "mainnet"))
ROLES = frozenset(("SCAN_RPC", "BROADCAST"))
REQUEST_FIELDS = frozenset(("action", "network_id", "txid"))
OBSERVER_TYPES = frozenset(("first_hop", "rpc_provider", "broadcast_peer",
                            "chain_observer", "global_observer"))
VISIBILITY = {
    # An encrypted transport does NOT hide the client's IP from its first hop.
    "first_hop": ("source_ip", "timestamp_ms", "transport"),
    "rpc_provider": ("request_kind", "timestamp_ms", "transport"),
    "broadcast_peer": ("txid", "timestamp_ms", "transport"),
    "chain_observer": ("txid", "block_height"),
    "global_observer": ("source_ip", "timestamp_ms", "txid",
                        "block_height", "transport"),
}
RESIDUAL_RISKS = {
    "first_hop": ("FIRST_HOP_ORIGIN_VISIBLE", "TIMING_CORRELATION_POSSIBLE"),
    "rpc_provider": ("RPC_METADATA_VISIBLE", "TIMING_CORRELATION_POSSIBLE"),
    "broadcast_peer": ("TX_SEEN_BY_PEER", "TIMING_CORRELATION_POSSIBLE"),
    "chain_observer": ("PUBLIC_CHAIN_LINKAGE_REMAINS",),
    "global_observer": ("GLOBAL_TIMING_CORRELATION_POSSIBLE",
                        "NO_GLOBAL_ANONYMITY_GUARANTEE"),
}


def _bounded_id(value: object) -> bool:
    return (type(value) is str and 0 < len(value) <= MAX_ID
            and all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "0123456789-._:" for c in value))


def _txid(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


@dataclass(frozen=True)
class Endpoint:
    endpoint_id: str
    provider_id: str
    role: str
    transport: str
    credential_scope: str
    available: bool


@dataclass(frozen=True)
class RoutePolicy:
    network_id: str
    privacy_required: bool = True
    allow_direct: bool = False
    shared_provider_mode: str = "DENY"  # DENY or explicit WARN (residual leak)
    permitted_transports: tuple[str, ...] = ("TOR", "I2P")


@dataclass(frozen=True)
class RouteDecision:
    status: str  # DENY / SELECTED_POLICY_ONLY
    endpoint_id: str | None = None
    transport: str | None = None
    risk_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionEvent:
    """Deliberately excludes IP, txid, endpoint, credentials, wallet metadata."""
    schema_version: int
    category: str
    code: str


@dataclass(frozen=True)
class SyntheticTrace:
    """Synthetic source details are for unit tests, NEVER logs or real traffic."""
    source_ip: str
    timestamp_ms: int
    transport: str
    request_kind: str
    txid: str
    block_height: int


@dataclass(frozen=True)
class ObserverReport:
    observer: str
    visible_fields: tuple[str, ...]
    residual_risks: tuple[str, ...]
    anonymity_claim: str = "NOT_ESTABLISHED"


def _valid_policy(policy: object) -> bool:
    if not isinstance(policy, RoutePolicy):
        return False
    if (policy.network_id not in NETWORKS
            or type(policy.privacy_required) is not bool
            or type(policy.allow_direct) is not bool
            or policy.shared_provider_mode not in ("DENY", "WARN")
            or type(policy.permitted_transports) is not tuple
            or not (1 <= len(policy.permitted_transports) <= 3)
            or len(set(policy.permitted_transports)) != len(policy.permitted_transports)
            or any(t not in TRANSPORT_PRIORITY for t in policy.permitted_transports)):
        return False
    if policy.privacy_required and (policy.allow_direct
                                    or "DIRECT" in policy.permitted_transports):
        return False
    if not policy.privacy_required and ("DIRECT" in policy.permitted_transports) != policy.allow_direct:
        return False
    return True


def _valid_endpoints(endpoints: object) -> bool:
    if (type(endpoints) is not tuple
            or not (1 <= len(endpoints) <= MAX_ENDPOINTS)
            or not all(isinstance(ep, Endpoint) for ep in endpoints)):
        return False
    seen: set[str] = set()
    for ep in endpoints:
        if (not _bounded_id(ep.endpoint_id)
                or not _bounded_id(ep.provider_id)
                or not _bounded_id(ep.credential_scope)
                or ep.role not in ROLES
                or ep.transport not in TRANSPORT_PRIORITY
                or type(ep.available) is not bool
                or ep.endpoint_id in seen):
            return False
        seen.add(ep.endpoint_id)
    return True


def _valid_request(request: object, policy: RoutePolicy) -> bool:
    return (isinstance(request, Mapping)
            and set(request) == REQUEST_FIELDS
            and request["action"] == "BROADCAST"
            and request["network_id"] == policy.network_id
            and _txid(request["txid"]))


def _cross_role_risks(endpoints: tuple[Endpoint, ...]) -> tuple[str, ...]:
    scan = [ep for ep in endpoints if ep.role == "SCAN_RPC"]
    broadcasts = [ep for ep in endpoints if ep.role == "BROADCAST"]
    risks: list[str] = []
    if any(a.credential_scope == b.credential_scope for a in scan for b in broadcasts):
        risks.append("CROSS_ROLE_CREDENTIAL_REUSE")
    if any(a.provider_id == b.provider_id for a in scan for b in broadcasts):
        risks.append("CROSS_ROLE_PROVIDER_CORRELATION")
    return tuple(risks)


def select_broadcast_route(
    request: Mapping[str, object], policy: RoutePolicy,
    endpoints: tuple[Endpoint, ...]
) -> tuple[RouteDecision, DecisionEvent]:
    """Pure deterministic local policy. No transaction submission is possible."""
    deny = (RouteDecision("DENY"), DecisionEvent(1, "ROUTE", "ROUTE_DENIED"))
    if not _valid_policy(policy) or not _valid_endpoints(endpoints):
        return deny
    if not _valid_request(request, policy):
        return deny

    risks = _cross_role_risks(endpoints)
    if "CROSS_ROLE_CREDENTIAL_REUSE" in risks:
        return deny  # Never share credentials between scanner and broadcaster.
    if risks and policy.shared_provider_mode == "DENY":
        return deny

    candidates = [ep for ep in endpoints if ep.role == "BROADCAST"
                  and ep.available
                  and ep.transport in policy.permitted_transports]
    if policy.privacy_required:
        candidates = [ep for ep in candidates if ep.transport != "DIRECT"]
    if not candidates:
        # Strict route failure. Never silently substitute clearnet.
        return deny
    candidates.sort(key=lambda ep: (
        TRANSPORT_PRIORITY.index(ep.transport), ep.endpoint_id
    ))
    selected = candidates[0]
    public_risks = tuple(code for code in risks if code == "CROSS_ROLE_PROVIDER_CORRELATION")
    if selected.transport == "DIRECT":
        public_risks += ("DIRECT_ORIGIN_METADATA_EXPOSED",)
    return (RouteDecision("SELECTED_POLICY_ONLY", selected.endpoint_id,
                          selected.transport, public_risks),
            DecisionEvent(1, "ROUTE", "ROUTE_POLICY_SELECTED"))


def observe_synthetic_trace(
    observer: object, trace: object
) -> ObserverReport | None:
    """Only returns a visibility schema, NOT actual trace data or identifiers."""
    if (type(observer) is not str or observer not in OBSERVER_TYPES
            or not isinstance(trace, SyntheticTrace)
            or not _bounded_id(trace.source_ip)
            or type(trace.timestamp_ms) is not int
            or not (0 <= trace.timestamp_ms <= MAX_TIMESTAMP)
            or trace.transport not in TRANSPORT_PRIORITY
            or trace.request_kind not in ("SCAN", "BROADCAST")
            or not _txid(trace.txid)
            or type(trace.block_height) is not int
            or not (0 <= trace.block_height <= 2_147_483_647)):
        return None
    return ObserverReport(observer, VISIBILITY[observer],
                          RESIDUAL_RISKS[observer])


def compare_synthetic_exposures(
    observer: str, before: SyntheticTrace, after: SyntheticTrace
) -> dict[str, object] | None:
    """Check only modeled field visibility, never conclude anonymity."""
    b = observe_synthetic_trace(observer, before)
    a = observe_synthetic_trace(observer, after)
    if b is None or a is None:
        return None
    return {
        "schema": 1,
        "observer": observer,
        "before_visible": b.visible_fields,
        "after_visible": a.visible_fields,
        "residual_risks": a.residual_risks,
        "anonymity_claim": "NOT_ESTABLISHED",
    }
