"""Research only: durable at-most-once provider invocation on trusted local storage."""
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from prototypes.signer_abstraction.model import SignedResult, SignerPolicy
from prototypes.signer_abstraction.provider import SignerGate, ProviderError, _validate_request

class PersistentSignerGate:
    def __init__(self, provider, journal_path, policy=None, *, signer_identity="research-fixture", provision=False):
        self.provider = provider
        self.policy = policy if policy is not None else SignerPolicy()
        if not isinstance(signer_identity, str) or not 1 <= len(signer_identity) <= 256:
            raise ProviderError("SIGNER_IDENTITY")
        self.signer_identity = signer_identity
        self.path = str(journal_path)
        if provision:
            # First-install only. Never provision automatically during recovery.
            # O_EXCL rejects an existing journal rather than resetting its history.
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                fd = os.open(self.path, flags, 0o600)
            except FileExistsError:
                raise ProviderError("JOURNAL_ALREADY_EXISTS") from None
            os.close(fd)
        db = self._db()
        try:
            if provision:
                db.execute("CREATE TABLE requests (id TEXT PRIMARY KEY, binding TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('RESERVED','COMPLETE')), digest TEXT, envelope BLOB)")
                db.commit()
            else:
                # A missing schema is never silently re-created.
                db.execute("SELECT id,binding,state,digest,envelope FROM requests LIMIT 0")
        finally:
            db.close()

    def _db(self):
        # mode=rw MUST NOT create a missing SQLite database, even mid-request.
        uri = Path(self.path).absolute().as_uri() + "?mode=rw"
        try:
            db = sqlite3.connect(uri, timeout=30, uri=True)
        except sqlite3.OperationalError:
            raise ProviderError("JOURNAL_UNAVAILABLE") from None
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA journal_mode=DELETE")
            return db
        except BaseException:
            db.close()
            raise

    def sign(self, request, approval):
        # Preserve frozen policy checks even on cached completion.
        _validate_request(request, approval, self.policy, self.provider.capabilities)
        request = replace(request, request_id=bytes.fromhex(request.request_id).hex(),
                          tx_digest=bytes.fromhex(request.tx_digest).hex())
        binding = hashlib.sha256(json.dumps(
            [asdict(request), asdict(approval), asdict(self.policy),
             self.signer_identity, asdict(self.provider.capabilities)],
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
