"""WAM Privacy V2-02: wallet-local, scope-bound selective disclosure.

This is a local data projection, NOT a ZK proof, public attestation, or a
permission to spend. Trusted UI and wallet data store must not be RPC-owned.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
from typing import Mapping, Sequence

from policy import (
    ConsentReceipt, PolicyAuthority, _canonical, _mac, _request_valid,
    _valid_key, MAX_TIMESTAMP,
)

MAX_WAM_ATOMS = 22_000_000 * 100_000_000
MAX_RECORDS = 1024
MAX_FIELDS = 3
MAX_DISCLOSURE_BYTES = 2048
SELECTABLE_FIELDS = frozenset(("txid", "amount_atoms", "block_height"))


@dataclass(frozen=True)
class WalletFact:
    """A minimal locally validated record; intentionally excludes private keys,
    account labels, memos, notes and recipient metadata.
    """
    account_scope: str
    resource_scope: str
    network_id: str
    txid: str
    amount_atoms: int
    block_height: int


@dataclass(frozen=True)
class SelectionReceipt:
    """Trusted UI confirmation of exact fields and one V2-01 consent nonce."""
    request_digest: str
    consent_nonce: str
    approved_fields: tuple[str, ...]
    expires_at: int
    mac: str


@dataclass(frozen=True)
class AuditEvent:
    """Only fixed decision codes, never resource/account/purpose/tx metadata."""
    schema_version: int
    action: str
    code: str


def _hex_token(value: object, size: int) -> bool:
    """Untrusted signed tokens must be bounded lowercase ASCII hex."""
    return (type(value) is str and len(value) == size
            and all(ch in "0123456789abcdef" for ch in value))


def _selection_fields(fields: object) -> bool:
    return (
        type(fields) is tuple
        and 1 <= len(fields) <= MAX_FIELDS
        and all(type(f) is str and f in SELECTABLE_FIELDS for f in fields)
        and tuple(sorted(set(fields))) == fields
    )


def _fact_valid(fact: object) -> bool:
    if not isinstance(fact, WalletFact):
        return False
    for value in (fact.account_scope, fact.resource_scope, fact.network_id):
        if type(value) is not str or not value or len(value) > 256 or value in ("*", "all"):
            return False
    return (
        type(fact.txid) is str
        and len(fact.txid) == 64
        and all(c in "0123456789abcdef" for c in fact.txid)
        and type(fact.amount_atoms) is int
        and 0 <= fact.amount_atoms <= MAX_WAM_ATOMS
        and type(fact.block_height) is int
        and 0 <= fact.block_height <= 2_147_483_647
    )


class LocalWalletFacts:
    """Wallet-owned, bounded and exact-scope store. Never inject RPC input here."""

    def __init__(self, facts: Sequence[WalletFact]):
        if (not isinstance(facts, (tuple, list))
                or len(facts) > MAX_RECORDS):
            raise ValueError("invalid local wallet record count")
        self._records: dict[tuple[str, str, str], WalletFact] = {}
        for fact in facts:
            if not _fact_valid(fact):
                raise ValueError("invalid local wallet fact")
            key = (fact.account_scope, fact.resource_scope, fact.network_id)
            if key in self._records:
                raise ValueError("duplicate local wallet fact scope")
            self._records[key] = fact

    def find(self, request: Mapping[str, object]) -> WalletFact | None:
        return self._records.get(
            (request["account_scope"], request["resource_scope"], request["network_id"])
        )


class SelectionIssuer:
    """Separate trusted UI-side field approval, not callable by remote clients."""

    def __init__(self, selection_key: bytes):
        if not _valid_key(selection_key):
            raise ValueError("selection key must be at least 32 bytes")
        self._key = selection_key

    def issue_after_user_confirmation(
        self, request: Mapping[str, object], consent: ConsentReceipt,
        fields: tuple[str, ...], *, expires_at: int
    ) -> SelectionReceipt:
        """Caller MUST obtain real UI confirmation of the displayed field list."""
        if (not _request_valid(request)
                or request["action"] != "DISCLOSE"
                or not isinstance(consent, ConsentReceipt)
                or not _hex_token(consent.nonce, 32)
                or not _selection_fields(fields)
                or type(expires_at) is not int
                or not 0 < expires_at <= MAX_TIMESTAMP):
            raise ValueError("invalid UI field approval")
        digest = hashlib.sha256(_canonical(dict(request))).hexdigest()
        obj = {
            "request_digest": digest,
            "consent_nonce": consent.nonce,
            "approved_fields": list(fields),
            "expires_at": expires_at,
        }
        return SelectionReceipt(
            digest, consent.nonce, fields, expires_at,
            _mac(self._key, b"WAM/V2/DisclosureFields/v1", obj),
        )


class DisclosureService:
    """Trusted wallet-local projection gate. Policy + UI consent both required."""

    def __init__(
        self, authority: PolicyAuthority, wallet_facts: LocalWalletFacts,
        selection_verify_key: bytes
    ):
        if not isinstance(authority, PolicyAuthority):
            raise ValueError("missing policy authority")
        if not isinstance(wallet_facts, LocalWalletFacts):
            raise ValueError("missing locally validated wallet source")
        if not _valid_key(selection_verify_key):
            raise ValueError("missing selection verifier key")
        self._authority = authority
        self._wallet = wallet_facts
        self._key = selection_verify_key

    @staticmethod
    def _event(allowed: bool) -> AuditEvent:
        return AuditEvent(1, "DISCLOSE", "DISCLOSE_RELEASED" if allowed else "DISCLOSE_DENIED")

    def disclose(
        self, request: Mapping[str, object], *, now: int,
        consent: ConsentReceipt | None, selection: SelectionReceipt | None
    ) -> tuple[dict[str, object] | None, AuditEvent]:
        """Never export on policy-only ALLOW without the exact validated fields."""
        deny = (None, self._event(False))
        if (not _request_valid(request)
                or request["action"] != "DISCLOSE"
                or type(now) is not int
                or not 0 <= now <= MAX_TIMESTAMP
                or not isinstance(consent, ConsentReceipt)
                or not isinstance(selection, SelectionReceipt)
                or not _selection_fields(selection.approved_fields)
                or not _hex_token(selection.request_digest, 64)
                or not _hex_token(selection.consent_nonce, 32)
                or not _hex_token(selection.mac, 64)
                or type(selection.expires_at) is not int
                or not 0 <= selection.expires_at <= MAX_TIMESTAMP
                or now >= selection.expires_at):
            return deny

        digest = hashlib.sha256(_canonical(dict(request))).hexdigest()
        if (selection.request_digest != digest
                or selection.consent_nonce != consent.nonce):
            return deny
        obj = {
            "request_digest": selection.request_digest,
            "consent_nonce": selection.consent_nonce,
            "approved_fields": list(selection.approved_fields),
            "expires_at": selection.expires_at,
        }
        if not hmac.compare_digest(
            selection.mac, _mac(self._key, b"WAM/V2/DisclosureFields/v1", obj)
        ):
            return deny

        record = self._wallet.find(request)
        if record is None:
            return deny
        values = {field: getattr(record, field) for field in selection.approved_fields}
        result: dict[str, object] = {
            "schema_version": 1,
            "network_id": request["network_id"],
            "resource_scope": request["resource_scope"],
            "purpose": request["purpose"],
            "facts": values,
        }
        if len(_canonical(result)) > MAX_DISCLOSURE_BYTES:
            return deny
        # Consume V2-01 one-use UI consent only once the selected projection
        # has passed all local checks. This does NOT grant spend/disclosure
        # outside this local function.
        if self._authority.authorize(request, now=now, consent=consent) != "ALLOW_POLICY_ONLY":
            return deny
        return result, self._event(True)
