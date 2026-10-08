"""WAM Privacy V2 standalone application-layer policy prototype.

No Core, signer, proof or consensus authority is implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

ACTIONS = frozenset({"SCAN", "VIEW", "SIGN", "BROADCAST", "DISCLOSE", "AUDIT"})
ROLES = frozenset({"scanner", "viewer", "signer", "broadcaster", "discloser", "auditor"})
ROLE_ACTION = dict(zip(sorted(ROLES), ("AUDIT", "BROADCAST", "DISCLOSE", "SCAN", "SIGN", "VIEW")))
# Explicit mapping; no transitive grants.
ROLE_ACTION = {
    "scanner": "SCAN", "viewer": "VIEW", "signer": "SIGN",
    "broadcaster": "BROADCAST", "discloser": "DISCLOSE", "auditor": "AUDIT",
}
FIELDS = frozenset({"actor_role", "capability_id", "action", "account_scope",
                    "resource_scope", "network_id", "purpose", "expires_at",
                    "session_id", "policy_version"})
MAX_FIELD = 256


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


def authorize(request: Mapping[str, object], grants: Mapping[str, Grant],
              revoked: frozenset[str], now: int,
              *, user_consented: bool = False,
              trusted_grants: bool = False) -> str:
    """Return DENY or ALLOW_POLICY_ONLY; never authorize signing or disclosure itself.

    Grants must originate from a separately authenticated local store.
    A policy ALLOW is only an input to a separately enforced signer/consent boundary.
    """
    if not trusted_grants or type(now) is not int:
        return "DENY"
    if not isinstance(request, Mapping) or set(request) != FIELDS:
        return "DENY"
    for key, value in request.items():
        if key in {"expires_at", "policy_version"}:
            if type(value) is not int:
                return "DENY"
        elif not isinstance(value, str) or not value or len(value) > MAX_FIELD:
            return "DENY"
    if request["policy_version"] != 2 or request["action"] not in ACTIONS:
        return "DENY"
    role = request["actor_role"]
    if role not in ROLES or ROLE_ACTION[role] != request["action"]:
        return "DENY"
    cap = request["capability_id"]
    if cap in revoked:
        return "DENY"
    grant = grants.get(cap)
    if not isinstance(grant, Grant):
        return "DENY"
    for field in FIELDS:
        if getattr(grant, field) != request[field]:
            return "DENY"
    if now >= grant.expires_at or now >= request["expires_at"]:
        return "DENY"
    if request["action"] == "DISCLOSE" and not user_consented:
        return "DENY"
    # SIGN still requires an independent signer, canonical tx and user approval.
    return "ALLOW_POLICY_ONLY"
