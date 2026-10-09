"""Research-only durable fail-closed composition of pinned SEC-001/SEC-002.

All three databases are trusted and outside attacker rollback domains.
No distributed ACID or whole-store rollback guarantee. Interrupted intents
remain blocked permanently: safety is retained at the cost of liveness.
"""
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from policy import _request_valid
from prototypes.signer_abstraction.model import SignedResult
from v2.sec001_research.durable_policy import DurablePolicy
from v2.sec002_research.journal import PersistentSignerGate


class RecoveryBlocked(ValueError):
    pass


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                         separators=(",", ":")).encode()).hexdigest()


class DurableResearchBridge:
    def __init__(self, authority, gate, path, *, account_scope,
                 provision=False, fault=None):
        if (not isinstance(authority, DurablePolicy)
                or not isinstance(gate, PersistentSignerGate)
                or gate.provider.capabilities.production is not False
                or type(account_scope) is not str or not account_scope
                or account_scope in ("*", "all")):
            raise RecoveryBlocked("UNQUALIFIED")
        self.authority, self.gate = authority, gate
        self.path, self.account_scope = str(path), account_scope
        # Trusted research fault injection callback, never request supplied.
        self.fault = fault or (lambda stage: None)
        if provision:
            # Trusted first install only: an existing journal is never reset.
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                fd = os.open(self.path, flags, 0o600)
            except FileExistsError:
                raise RecoveryBlocked("COORDINATOR_ALREADY_EXISTS") from None
            except OSError:
                raise RecoveryBlocked("COORDINATOR_UNAVAILABLE") from None
            os.close(fd)
        db = self._db()
        try:
            if provision:
                db.execute("CREATE TABLE intents (id TEXT PRIMARY KEY, "
                           "binding TEXT NOT NULL, state TEXT NOT NULL, "
                           "generation INTEGER, capability TEXT NOT NULL, "
                           "digest TEXT, envelope BLOB)")
                db.commit()
            # Missing schema never creates a replacement.
            db.execute("SELECT id FROM intents LIMIT 1").fetchall()
        finally:
            db.close()

    def _db(self):
        # mode=rw never recreates an unlinked journal during restart or retry.
        uri = Path(self.path).absolute().as_uri() + "?mode=rw"
        try:
            db = sqlite3.connect(uri, timeout=30, uri=True)
        except sqlite3.OperationalError:
            raise RecoveryBlocked("COORDINATOR_UNAVAILABLE") from None
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA journal_mode=DELETE")
            return db
        except BaseException:
            db.close()
            raise

    def _transition(self, request_id, expected, proposed, **fields):
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            # Column names are fixed internal arguments, never untrusted.
            columns = ["state=?"] + [name + "=?" for name in fields]
            values = [proposed] + list(fields.values()) + [request_id, expected]
            changed = db.execute("UPDATE intents SET " + ",".join(columns)
                                 + " WHERE id=? AND state=?", values).rowcount
            if changed != 1:
                raise RecoveryBlocked("INTENT_CONFLICT")
            db.commit()
        finally:
            db.close()

    def _signer_receipt(self, request, approval, result=None):
        expected = _digest([asdict(request), asdict(approval), asdict(self.gate.policy),
                            self.gate.signer_identity, asdict(self.gate.provider.capabilities)])
        # Trusted adapter-owned storage read only; no schema mutation.
        db = sqlite3.connect(Path(self.gate.path).absolute().as_uri() + "?mode=ro", uri=True)
        try:
            row = db.execute("SELECT binding,state,digest,envelope FROM requests WHERE id=?",
                             (request.request_id,)).fetchone()
        finally:
            db.close()
        if (row is None or row[0] != expected or row[1] != "COMPLETE"
                or row[2] != request.tx_digest
                or type(row[3]) is not bytes or not row[3]
                or (result is not None and (row[2], row[3]) !=
                    (result.tx_digest, result.envelope))):
            raise RecoveryBlocked("SIGNER_RECEIPT_INVALID")
        return SignedResult(request.request_id, row[2], row[3])

    def _policy_receipt(self, capability_request, minimum_generation, now):
        checkpoint = self.authority.export_checkpoint()
        state = json.loads(checkpoint["snapshot"])["state"]
        capability = capability_request.get("capability_id")
        grant = state["grants"].get(capability)
        if (checkpoint["generation"] < minimum_generation
                or capability not in state["used"]
                or capability in state["revoked"]
                or now < state["highwater"]
                or not grant or grant["grant"]["single_use"] is not True
                or now >= grant["grant"]["expires_at"]
                or any(grant["grant"].get(k) != v
                       for k, v in capability_request.items())):
            raise RecoveryBlocked("POLICY_RECEIPT_INVALID")
        return checkpoint["generation"]

    def sign(self, capability_request, request, approval, *, now):
        try:
            capability_request = dict(capability_request)
        except (TypeError, ValueError):
            raise RecoveryBlocked("BRIDGE_DENIED") from None
        if not _request_valid(capability_request):
            raise RecoveryBlocked("BRIDGE_DENIED")
        request.validate_shape()
        approval.validate()
        if (request.network not in ("regtest", "testnet")
                or type(now) is not int or not 0 <= now < (1 << 63)
                or capability_request.get("action") != "SIGN"
                or capability_request.get("actor_role") != "signer"
                or capability_request.get("resource_scope") != request.request_id
                or capability_request.get("network_id") != request.network
                or capability_request.get("account_scope") != self.account_scope):
            raise RecoveryBlocked("BRIDGE_DENIED")
        request = replace(request, request_id=bytes.fromhex(request.request_id).hex(),
                          tx_digest=bytes.fromhex(request.tx_digest).hex())
        binding = _digest([dict(capability_request), asdict(request), asdict(approval),
                           asdict(self.gate.policy), self.gate.signer_identity,
                           asdict(self.gate.provider.capabilities), self.account_scope])
        capability = capability_request.get("capability_id")
        checkpoint = self.authority.export_checkpoint()
        state = json.loads(checkpoint["snapshot"])["state"]
        grant = state["grants"].get(capability)
        if not grant or grant["grant"]["single_use"] is not True:
            raise RecoveryBlocked("SINGLE_USE_REQUIRED")
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT binding,state,generation,capability,digest,envelope "
                             "FROM intents WHERE id=?", (request.request_id,)).fetchone()
            if row:
                if row[0] != binding:
                    raise RecoveryBlocked("REQUEST_BINDING_MISMATCH")
                if row[1] != "COMPLETE":
                    raise RecoveryBlocked("INTENT_UNCERTAIN")
                self._policy_receipt(capability_request, row[2], now)
                result = self._signer_receipt(request, approval)
                if (row[4], row[5]) != (result.tx_digest, result.envelope):
                    raise RecoveryBlocked("RESULT_RECEIPT_INVALID")
                db.commit()
                return result
            db.execute("INSERT INTO intents(id,binding,state,generation,capability) "
                       "VALUES (?,?,'PREPARED',?,?)",
                       (request.request_id, binding, checkpoint["generation"], capability))
            db.commit()
        finally:
            db.close()
        self.fault("PREPARED")
        if self.authority.authorize(capability_request, now=now) != "ALLOW_POLICY_ONLY":
            self._transition(request.request_id, "PREPARED", "DENIED")
            raise RecoveryBlocked("POLICY_DENIED")
        self.fault("POLICY_COMMITTED")
        generation = self._policy_receipt(capability_request, checkpoint["generation"] + 1, now)
        self._transition(request.request_id, "PREPARED", "POLICY_SPENT",
                         generation=generation)
        self.fault("POLICY_SPENT")
        self._transition(request.request_id, "POLICY_SPENT", "SIGNING")
        self.fault("SIGNING")
        # B durably reserves before provider invocation; exceptions stay SIGNING.
        result = self.gate.sign(request, approval)
        self.fault("SIGNER_COMPLETE")
        self._signer_receipt(request, approval, result)
        self._transition(request.request_id, "SIGNING", "COMPLETE",
                         digest=result.tx_digest, envelope=result.envelope)
        self.fault("COMPLETE")
        return result
