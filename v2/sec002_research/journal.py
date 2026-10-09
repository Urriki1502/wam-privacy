"""Research only: durable at-most-once provider invocation on trusted local storage."""
from dataclasses import asdict, replace
import hashlib
import json
import sqlite3
from prototypes.signer_abstraction.model import SignedResult, SignerPolicy
from prototypes.signer_abstraction.provider import SignerGate, ProviderError, _validate_request

class PersistentSignerGate:
    def __init__(self, provider, journal_path, policy=None):
        self.provider = provider
        self.policy = policy if policy is not None else SignerPolicy()
        self.path = str(journal_path)
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, binding TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('RESERVED','COMPLETE')), digest TEXT, envelope BLOB)")

    def _db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")
        return db

    def sign(self, request, approval):
        # Preserve frozen policy checks even on cached completion.
        _validate_request(request, approval, self.policy, self.provider.capabilities)
        request = replace(request, request_id=bytes.fromhex(request.request_id).hex(),
                          tx_digest=bytes.fromhex(request.tx_digest).hex())
        binding = hashlib.sha256(json.dumps(
            [asdict(request), asdict(approval), asdict(self.policy)],
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT binding,state,digest,envelope FROM requests WHERE id=?",
                             (request.request_id,)).fetchone()
            if row:
                if row[0] != binding:
                    raise ProviderError("REQUEST_BINDING_MISMATCH")
                if row[1] != "COMPLETE":
                    raise ProviderError("REQUEST_PENDING")
                if row[2] != request.tx_digest or not isinstance(row[3], bytes) or not row[3]:
                    raise ProviderError("JOURNAL_CORRUPT")
                db.commit()
                return SignedResult(request.request_id, row[2], row[3])
            db.execute("INSERT INTO requests(id,binding,state) VALUES (?,?,'RESERVED')",
                       (request.request_id, binding))
            db.commit()
        finally:
            db.close()
        # Crash or provider uncertainty from here permanently retains RESERVED.
        result = SignerGate(self.provider, self.policy).sign(request, approval)
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("UPDATE requests SET state='COMPLETE',digest=?,envelope=? WHERE id=? AND binding=? AND state='RESERVED'",
                                 (result.tx_digest, result.envelope, request.request_id, binding)).rowcount
            if changed != 1:
                raise ProviderError("JOURNAL_CONFLICT")
            db.commit()
        finally:
            db.close()
        return result
