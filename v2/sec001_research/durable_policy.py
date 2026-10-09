"""SEC-001 research: durable wrapper over the immutable V2 policy.

The database is TRUSTED EXTERNAL CHECKPOINT STORAGE, outside the rollback
domain of exported wallet snapshots. SQLite alone cannot detect rollback of
the entire trusted store. Never expose this adapter or its keys through RPC.
"""
import hashlib
import sqlite3
from policy import PolicyAuthority
from v2.sec001_research.witness import CheckpointStamp, stamp_for


class CheckpointRejected(ValueError):
    pass


class DurablePolicy:
    def __init__(self, path, grant_key, consent_key, *, provision=False, checkpoint_witness=None):
        self.path = str(path)
        # Optional research adapter: the witness itself MUST live outside the
        # rollbackable wallet DB and support atomic durable compare-and-advance.
        # Without this adapter, a valid whole-DB rollback remains undetectable.
        self._witness = checkpoint_witness
        self._grant_key, self._consent_key = grant_key, consent_key
        self._conn = sqlite3.connect(self.path, timeout=10, isolation_level=None,
                                     check_same_thread=False)
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA journal_mode=DELETE")
        # Per-instance threads serialize; separate processes/connections serialize
        # at BEGIN IMMEDIATE. Keys are validated by the frozen authority.
        import threading
        self._lock = threading.RLock()
        initial = PolicyAuthority(grant_key, consent_key).snapshot()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                if provision:
                    self._conn.execute("CREATE TABLE IF NOT EXISTS checkpoint "
                                       "(id INTEGER PRIMARY KEY CHECK(id=1), "
                                       "generation INTEGER NOT NULL, snapshot TEXT NOT NULL)")
                    self._conn.execute("INSERT OR IGNORE INTO checkpoint VALUES(1,0,?)",
                                       (initial,))
                self._read()
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                self._conn.close()
                raise CheckpointRejected("CHECKPOINT_UNAVAILABLE") from None

    def _read(self):
        row = self._conn.execute(
            "SELECT generation,snapshot FROM checkpoint WHERE id=1").fetchone()
        if row is None or type(row[0]) is not int or row[0] < 0:
            raise CheckpointRejected("CHECKPOINT_UNAVAILABLE")
        # Always authenticate the stored authority; corrupt state never resets.
        authority = PolicyAuthority.restore(row[1], self._grant_key, self._consent_key)
        if self._witness is not None:
            # A valid HMAC on old policy bytes does not prove freshness.
            # Compare against an independently protected generation + digest.
            try:
                observed = self._witness.read()
            except Exception:
                raise CheckpointRejected("CHECKPOINT_WITNESS_UNAVAILABLE") from None
            if (type(observed) is not CheckpointStamp
                    or observed != stamp_for(row[0], row[1])):
                raise CheckpointRejected("CHECKPOINT_ROLLBACK_OR_FORK")
        return row[0], row[1], authority

    def _apply(self, operation):
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                generation, _, authority = self._read()
                result = operation(authority)
                if generation >= (1 << 63) - 1:
                    raise CheckpointRejected("CHECKPOINT_EXHAUSTED")
                next_snapshot = authority.snapshot()
                if self._witness is not None:
                    # Security-first ordering: trusted witness MUST commit
                    # before SQLite. Crash in between makes the store fail
                    # closed at restart instead of resurrecting old grants.
                    current = self._conn.execute(
                        "SELECT snapshot FROM checkpoint WHERE id=1").fetchone()[0]
                    try:
                        self._witness.advance(
                            stamp_for(generation, current),
                            stamp_for(generation + 1, next_snapshot))
                    except Exception:
                        raise CheckpointRejected("CHECKPOINT_WITNESS_ADVANCE_FAILED") from None
                self._conn.execute("UPDATE checkpoint SET generation=?,snapshot=? WHERE id=1",
                                   (generation + 1, next_snapshot))
                # No ALLOW or external side effect before durable commit.
                self._conn.execute("COMMIT")
                return result
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    def issue_local_grant(self, grant):
        return self._apply(lambda a: a.issue_local_grant(grant))

    def revoke(self, capability_id):
        return self._apply(lambda a: a.revoke(capability_id))

    def authorize(self, request, *, now, consent=None):
        return self._apply(lambda a: a.authorize(request, now=now, consent=consent))

    def checkpoint_stamp(self):
        """Public non-secret digest for trusted installer/review, NOT authority."""
        with self._lock:
            generation, snapshot, _ = self._read()
            return stamp_for(generation, snapshot)

    def export_checkpoint(self):
        with self._lock:
            generation, snapshot, _ = self._read()
            return {"generation": generation, "snapshot": snapshot,
                    "sha256": hashlib.sha256(snapshot.encode("ascii")).hexdigest()}

    def validate_checkpoint(self, checkpoint):
        # External data is never installed into trusted state. Exact equality
        # also rejects same-generation forks, future generations and tampering.
        with self._lock:
            current = self.export_checkpoint()
            if type(checkpoint) is not dict or checkpoint != current:
                raise CheckpointRejected("CHECKPOINT_STALE_OR_INVALID")
            return current["generation"]

    def close(self):
        with self._lock:
            self._conn.close()
