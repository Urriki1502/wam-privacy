"""WAM Privacy V2-01: isolated, fail-closed application-layer capability policy.

TRUST BOUNDARY: PolicyAuthority and ConsentIssuer are held by trusted LOCAL
wallet/UI code. Never expose their issuance methods or HMAC keys to an RPC
caller. A policy ALLOW is not a signature, transaction approval or disclosure.
No Core, chain, verifier, network or consensus behavior is implemented here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import secrets
from typing import Mapping

ACTIONS = frozenset(("SCAN", "VIEW", "SIGN", "BROADCAST", "DISCLOSE", "AUDIT"))
ROLE_ACTION = {
    "scanner": "SCAN",
    "viewer": "VIEW",
    "signer": "SIGN",
    "broadcaster": "BROADCAST",
    "discloser": "DISCLOSE",
    "auditor": "AUDIT",
}
FIELDS = frozenset((
    "actor_role", "capability_id", "action", "account_scope", "resource_scope",
    "network_id", "purpose", "expires_at", "session_id", "policy_version",
))
MAX_FIELD = 256
MAX_GRANTS = 4096
MAX_SNAPSHOT_BYTES = 1_000_000
MAX_TIMESTAMP = (1 << 63) - 1


@dataclass(frozen=True)
class Grant:
    capability_id: str
    actor_role: str
    action: str
    account_scope: str
    resource_scope: str
    network_id: str
    purpose: str
    expires_at: int
    session_id: str
    policy_version: int = 2
    single_use: bool = False


@dataclass(frozen=True)
class ConsentReceipt:
    """Proof that a separate trusted LOCAL UI issuer approved this exact request."""
    request_digest: str
    nonce: str
    expires_at: int
    mac: str


def _canonical(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _mac(key: bytes, domain: bytes, obj: object) -> str:
    return hmac.new(key, domain + b"\0" + _canonical(obj), hashlib.sha256).hexdigest()


def _request_valid(request: object) -> bool:
    if not isinstance(request, Mapping) or set(request) != FIELDS:
        return False
    for name, value in request.items():
        if name in ("expires_at", "policy_version"):
            if type(value) is not int or not (0 <= value <= MAX_TIMESTAMP):
                return False
        elif type(value) is not str or not value or len(value) > MAX_FIELD:
            return False
    if request["policy_version"] != 2:
        return False
    if request["action"] not in ACTIONS:
        return False
    role = request["actor_role"]
    if role not in ROLE_ACTION or ROLE_ACTION[role] != request["action"]:
        return False
    # No wildcard authority. An issuer must specify a concrete account/resource.
    if request["account_scope"] in ("*", "all") or request["resource_scope"] in ("*", "all"):
        return False
    return True


def _hex_token(value: object, size: int) -> bool:
    """Reject non-ASCII or malformed untrusted HMAC tokens before comparison."""
    return (type(value) is str and len(value) == size
            and all(ch in "0123456789abcdef" for ch in value))


def _valid_key(key: bytes) -> bool:
    return type(key) is bytes and len(key) >= 32


class ConsentIssuer:
    """Separate trusted UI-side issuer. Never expose to the untrusted request path."""

    def __init__(self, consent_key: bytes):
        if not _valid_key(consent_key):
            raise ValueError("consent key must be at least 32 bytes")
        self._key = consent_key

    def issue_after_user_confirmation(self, request: Mapping[str, object],
                                      *, expires_at: int) -> ConsentReceipt:
        """Call ONLY after the trusted UI has independently verified user intent.

        This method itself is NOT a UI or proof of user presence.
        """
        if not _request_valid(request) or request["action"] != "DISCLOSE":
            raise ValueError("invalid disclosure request")
        if type(expires_at) is not int or not (0 < expires_at <= MAX_TIMESTAMP):
            raise ValueError("invalid consent expiry")
        digest = hashlib.sha256(_canonical(dict(request))).hexdigest()
        nonce = secrets.token_hex(16)
        payload = {"request_digest": digest, "nonce": nonce, "expires_at": expires_at}
        return ConsentReceipt(digest, nonce, expires_at,
                              _mac(self._key, b"WAM/V2/Consent/v1", payload))


class PolicyAuthority:
    """Locally authenticated grant ledger; NOT an untrusted RPC service.

    The caller supplies untrusted requests only. Trusted wallet code controls
    this authority, the clock and the separate consent issuer. Snapshot MAC
    rejects tampering, but anti-rollback of an old *valid* snapshot needs
    trusted external monotonic storage in the eventual wallet integration.
    """

    def __init__(self, grant_key: bytes, consent_verify_key: bytes):
        if not _valid_key(grant_key) or not _valid_key(consent_verify_key):
            raise ValueError("policy and consent keys must be at least 32 bytes")
        self._key = grant_key
        self._consent_key = consent_verify_key
        self._grants: dict[str, tuple[Grant, str]] = {}
        self._revoked: set[str] = set()
        self._used: set[str] = set()
        self._consent_used: set[str] = set()
        self._highwater = -1

    def issue_local_grant(self, grant: Grant) -> None:
        """Trusted local grant provisioning; never callable by a remote requester."""
        if not isinstance(grant, Grant) or type(grant.single_use) is not bool:
            raise ValueError("invalid grant")
        data = asdict(grant)
        request = {name: data[name] for name in FIELDS}
        if not _request_valid(request):
            raise ValueError("invalid grant scope, role or expiry")
        if grant.capability_id in self._grants or len(self._grants) >= MAX_GRANTS:
            raise ValueError("duplicate grant or grant limit")
        seal = _mac(self._key, b"WAM/V2/Grant/v1", data)
        self._grants[grant.capability_id] = (grant, seal)

    def revoke(self, capability_id: str) -> None:
        if capability_id not in self._grants:
            raise ValueError("unknown grant")
        self._revoked.add(capability_id)

    def authorize(self, request: Mapping[str, object], *, now: int,
                  consent: ConsentReceipt | None = None) -> str:
        """Policy-only answer. SIGN and DISCLOSE require independent enforcement."""
        if type(now) is not int or not (0 <= now <= MAX_TIMESTAMP):
            return "DENY"
        # Clock supplied by trusted local adapter, never by an RPC request.
        if now < self._highwater:
            return "DENY"
        self._highwater = now
        if not _request_valid(request):
            return "DENY"
        cap = request["capability_id"]
        if cap in self._revoked or cap in self._used:
            return "DENY"
        item = self._grants.get(cap)
        if item is None:
            return "DENY"
        grant, seal = item
        if not hmac.compare_digest(
            seal, _mac(self._key, b"WAM/V2/Grant/v1", asdict(grant))
        ):
            return "DENY"
        data = asdict(grant)
        if any(data[name] != request[name] for name in FIELDS):
            return "DENY"
        if now >= grant.expires_at:
            return "DENY"

        if grant.action == "DISCLOSE":
            if not isinstance(consent, ConsentReceipt):
                return "DENY"
            digest = hashlib.sha256(_canonical(dict(request))).hexdigest()
            payload = {"request_digest": consent.request_digest,
                       "nonce": consent.nonce, "expires_at": consent.expires_at}
            if (not _hex_token(consent.request_digest, 64)
                    or not _hex_token(consent.nonce, 32)
                    or not _hex_token(consent.mac, 64)
                    or type(consent.expires_at) is not int
                    or not 0 <= consent.expires_at <= MAX_TIMESTAMP
                    or consent.request_digest != digest
                    or len(consent.nonce) != 32
                    or consent.nonce in self._consent_used
                    or now >= consent.expires_at
                    or not hmac.compare_digest(
                        consent.mac,
                        _mac(self._consent_key, b"WAM/V2/Consent/v1", payload)
                    )):
                return "DENY"
        elif consent is not None:
            return "DENY"

        if grant.single_use:
            self._used.add(cap)
        if consent is not None:
            self._consent_used.add(consent.nonce)
        return "ALLOW_POLICY_ONLY"

    def snapshot(self) -> str:
        """Signed local state for restart/revocation/replay regression only."""
        state = {
            "schema": 1,
            "grants": {cap: {"grant": asdict(g), "mac": signature}
                       for cap, (g, signature) in sorted(self._grants.items())},
            "revoked": sorted(self._revoked),
            "used": sorted(self._used),
            "consent_used": sorted(self._consent_used),
            "highwater": self._highwater,
        }
        envelope = {"state": state, "mac": _mac(self._key, b"WAM/V2/Snapshot/v1", state)}
        serialized = _canonical(envelope).decode("ascii")
        if len(serialized) > MAX_SNAPSHOT_BYTES:
            raise ValueError("snapshot too large")
        return serialized

    @classmethod
    def restore(cls, serialized: str, grant_key: bytes,
                consent_verify_key: bytes) -> "PolicyAuthority":
        if (type(serialized) is not str
                or len(serialized) > MAX_SNAPSHOT_BYTES):
            raise ValueError("invalid snapshot size")
        authority = cls(grant_key, consent_verify_key)
        try:
            envelope = json.loads(serialized)
            if not isinstance(envelope, dict) or set(envelope) != {"state", "mac"}:
                raise ValueError("snapshot envelope shape")
            state, seal = envelope["state"], envelope["mac"]
            if type(seal) is not str or not hmac.compare_digest(
                seal, _mac(grant_key, b"WAM/V2/Snapshot/v1", state)
            ):
                raise ValueError("snapshot authentication")
            if not isinstance(state, dict) or set(state) != {
                "schema", "grants", "revoked", "used", "consent_used", "highwater"
            } or state["schema"] != 1:
                raise ValueError("snapshot schema")
            entries = state["grants"]
            if not isinstance(entries, dict) or len(entries) > MAX_GRANTS:
                raise ValueError("snapshot grants")
            for cap, item in entries.items():
                if not isinstance(item, dict) or set(item) != {"grant", "mac"}:
                    raise ValueError("grant entry shape")
                grant = Grant(**item["grant"])
                if cap != grant.capability_id or type(grant.single_use) is not bool:
                    raise ValueError("grant identity")
                request = {name: getattr(grant, name) for name in FIELDS}
                if not _request_valid(request):
                    raise ValueError("grant validity")
                if type(item["mac"]) is not str or not hmac.compare_digest(
                    item["mac"], _mac(grant_key, b"WAM/V2/Grant/v1", asdict(grant))
                ):
                    raise ValueError("grant authentication")
                authority._grants[cap] = (grant, item["mac"])
            for field in ("revoked", "used", "consent_used"):
                values = state[field]
                if (not isinstance(values, list)
                        or not all(type(v) is str and 0 < len(v) <= MAX_FIELD for v in values)
                        or len(set(values)) != len(values)):
                    raise ValueError("invalid state set")
            if not set(state["revoked"]) <= set(entries) or not set(state["used"]) <= set(entries):
                raise ValueError("unknown grant in state")
            highwater = state["highwater"]
            if type(highwater) is not int or not (-1 <= highwater <= MAX_TIMESTAMP):
                raise ValueError("invalid clock witness")
            authority._revoked = set(state["revoked"])
            authority._used = set(state["used"])
            authority._consent_used = set(state["consent_used"])
            authority._highwater = highwater
        except (TypeError, KeyError, ValueError, AttributeError, OverflowError) as exc:
            raise ValueError("invalid authenticated policy snapshot") from exc
        return authority
