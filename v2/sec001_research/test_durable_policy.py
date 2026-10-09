"""Local synthetic defensive tests against frozen v2.policy."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from policy import ConsentIssuer, Grant
from v2.sec001_research.durable_policy import DurablePolicy, CheckpointRejected
from v2.sec001_research.witness import CheckpointStamp
import threading

GKEY = b"G" * 32
CKEY = b"C" * 32

class MemoryWitnessForTests:
    """Trusted independent highwater *fixture*, not production secure storage."""
    def __init__(self, stamp):
        self._stamp = stamp
        self._lock = threading.Lock()
        self.available = True
        self.fail_advance = False

    def read(self):
        with self._lock:
            if not self.available:
                raise OSError("witness offline")
            return self._stamp

    def advance(self, expected, updated):
        with self._lock:
            if not self.available or self.fail_advance:
                raise OSError("witness unavailable")
            if (self._stamp != expected
                    or type(updated) is not CheckpointStamp
                    or updated.generation != expected.generation + 1):
                raise ValueError("nonmonotonic witness")
            self._stamp = updated


class DurableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "trusted.sqlite"
        self.a = DurablePolicy(self.path, GKEY, CKEY, provision=True)
        self.grant = Grant("cap", "scanner", "SCAN", "account", "resource",
                           "regtest", "scan", 1000, "session", single_use=True)
        self.a.issue_local_grant(self.grant)
        self.request = {k:v for k,v in asdict(self.grant).items() if k != "single_use"}

    def tearDown(self):
        self.a.close()
        self.tmp.cleanup()

    def restart(self, *, witness=None):
        self.a.close()
        self.a = DurablePolicy(self.path, GKEY, CKEY, checkpoint_witness=witness)

    def trusted_witness(self):
        w = MemoryWitnessForTests(self.a.checkpoint_stamp())
        self.restart(witness=w)
        return w

    def test_single_use_durable_before_allow(self):
        old = self.a.export_checkpoint()
        self.assertEqual(self.a.authorize(self.request, now=100), "ALLOW_POLICY_ONLY")
        self.restart()
        self.assertEqual(self.a.authorize(self.request, now=101), "DENY")
        with self.assertRaises(CheckpointRejected):
            self.a.validate_checkpoint(old)

    def test_revoke_restart_and_old_authenticated_snapshot(self):
        old = self.a.export_checkpoint()
        self.a.revoke("cap")
        self.restart()
        self.assertEqual(self.a.authorize(self.request, now=100), "DENY")
        with self.assertRaises(CheckpointRejected):
            self.a.validate_checkpoint(old)

    def test_grant_survives_restart(self):
        self.restart()
        self.assertEqual(self.a.authorize(self.request, now=100), "ALLOW_POLICY_ONLY")

    def test_consent_nonce_survives_restart(self):
        g = replace(self.grant, capability_id="disclose", actor_role="discloser",
                    action="DISCLOSE", single_use=False)
        self.a.issue_local_grant(g)
        req = {k:v for k,v in asdict(g).items() if k != "single_use"}
        consent = ConsentIssuer(CKEY).issue_after_user_confirmation(req, expires_at=500)
        self.assertEqual(self.a.authorize(req, now=100, consent=consent), "ALLOW_POLICY_ONLY")
        self.restart()
        self.assertEqual(self.a.authorize(req, now=101, consent=consent), "DENY")

    def test_clock_highwater_durable_even_on_denial(self):
        self.assertEqual(self.a.authorize({}, now=500), "DENY")
        self.restart()
        self.assertEqual(self.a.authorize(self.request, now=499), "DENY")

    def test_checkpoint_tamper_future_fork_shape(self):
        cp = self.a.export_checkpoint()
        for bad in ({**cp, "generation": cp["generation"]+1},
                    {**cp, "snapshot": cp["snapshot"]+" "},
                    {**cp, "sha256": "0"*64}, [], {}):
            with self.subTest(bad=repr(bad)[:40]), self.assertRaises(CheckpointRejected):
                self.a.validate_checkpoint(bad)
        self.assertEqual(self.a.validate_checkpoint(cp), cp["generation"])

    def test_two_connections_single_winner(self):
        b = DurablePolicy(self.path, GKEY, CKEY)
        try:
            with ThreadPoolExecutor(2) as pool:
                results = list(pool.map(lambda a: a.authorize(self.request, now=100),
                                        (self.a, b)))
            self.assertEqual(sorted(results), ["ALLOW_POLICY_ONLY", "DENY"])
        finally:
            b.close()

    def test_missing_store_fails_closed_without_provision(self):
        with self.assertRaises(CheckpointRejected):
            DurablePolicy(Path(self.tmp.name)/"absent.sqlite", GKEY, CKEY)

    def test_wrong_key_fails_closed(self):
        with self.assertRaises(CheckpointRejected):
            DurablePolicy(self.path, b"X"*32, CKEY)

    def test_corrupt_trusted_snapshot_never_resets(self):
        cp = self.a.export_checkpoint()
        self.a._conn.execute("UPDATE checkpoint SET snapshot='invalid'")
        with self.assertRaises(ValueError):
            self.a.authorize(self.request, now=100)
        self.a._conn.execute("UPDATE checkpoint SET snapshot=?", (cp["snapshot"],))

    def test_process_crash_uncommitted_update_rolls_back(self):
        before = self.a.export_checkpoint()
        script = (
            "import sqlite3,os,sys\n"
            "c=sqlite3.connect(sys.argv[1],isolation_level=None)\n"
            "c.execute('PRAGMA synchronous=FULL')\n"
            "c.execute('BEGIN IMMEDIATE')\n"
            "c.execute(\"UPDATE checkpoint SET generation=999,snapshot='invalid'\")\n"
            "os._exit(77)\n")
        result = subprocess.run([sys.executable, "-c", script, str(self.path)], check=False)
        self.assertEqual(result.returncode, 77)
        self.restart()
        self.assertEqual(self.a.export_checkpoint(), before)
        self.assertEqual(self.a.authorize(self.request, now=100), "ALLOW_POLICY_ONLY")

    def test_failed_mutation_is_atomic(self):
        before = self.a.export_checkpoint()
        with self.assertRaises(ValueError):
            self.a.issue_local_grant(self.grant)
        self.assertEqual(self.a.export_checkpoint(), before)

    def test_external_witness_rejects_old_hmac_valid_full_store_rollback(self):
        older = self.a.export_checkpoint()
        w = self.trusted_witness()
        self.a.revoke("cap")
        self.assertGreater(w.read().generation, older["generation"])
        self.a.close()
        # Attacker restores an older but authenticated DB row.
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE checkpoint SET generation=?,snapshot=? WHERE id=1",
                      (older["generation"], older["snapshot"]))
        with self.assertRaises(CheckpointRejected):
            DurablePolicy(self.path, GKEY, CKEY, checkpoint_witness=w)

    def test_without_external_witness_full_store_rollback_is_still_possible(self):
        old = self.a.export_checkpoint()
        self.a.revoke("cap")
        self.a.close()
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE checkpoint SET generation=?,snapshot=? WHERE id=1",
                      (old["generation"], old["snapshot"]))
        self.a = DurablePolicy(self.path, GKEY, CKEY)
        # NEGATIVE SECURITY EVIDENCE: this is why the research default is
        # not an adequate rollback-resistant production wallet backend.
        self.assertEqual(self.a.authorize(self.request, now=100), "ALLOW_POLICY_ONLY")

    def test_external_witness_persists_revoke_and_single_use_across_restart(self):
        w = self.trusted_witness()
        self.assertEqual(self.a.authorize(self.request, now=100), "ALLOW_POLICY_ONLY")
        self.restart(witness=w)
        self.assertEqual(self.a.authorize(self.request, now=101), "DENY")
        self.a.revoke("cap")
        self.restart(witness=w)
        self.assertEqual(self.a.authorize(self.request, now=102), "DENY")
        self.assertEqual(self.a.checkpoint_stamp(), w.read())

    def test_external_witness_rejects_same_generation_state_fork(self):
        w = self.trusted_witness()
        row = self.a.export_checkpoint()
        changed = row["snapshot"].replace('"highwater":-1', '"highwater":0')
        # A forged-but-MAC-invalid state is already rejected by V2.
        self.assertNotEqual(changed, row["snapshot"])
        self.a.close()
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE checkpoint SET snapshot=? WHERE id=1", (changed,))
        with self.assertRaises(CheckpointRejected):
            DurablePolicy(self.path, GKEY, CKEY, checkpoint_witness=w)

    def test_external_witness_unavailable_fails_closed(self):
        w = self.trusted_witness()
        w.available = False
        with self.assertRaises(CheckpointRejected):
            self.a.authorize(self.request, now=100)
        self.assertEqual(self.a._conn.execute(
            "SELECT generation FROM checkpoint").fetchone()[0], 1)
        w.available = True
        self.assertEqual(self.a.authorize(self.request, now=100), "ALLOW_POLICY_ONLY")

    def test_external_witness_advance_failure_does_not_commit_policy(self):
        w = self.trusted_witness()
        before = self.a.export_checkpoint()
        w.fail_advance = True
        with self.assertRaises(CheckpointRejected):
            self.a.revoke("cap")
        w.fail_advance = False
        self.assertEqual(self.a.export_checkpoint(), before)
        self.assertEqual(self.a.authorize(self.request, now=100), "ALLOW_POLICY_ONLY")

    def test_after_witness_advance_but_before_db_commit_restart_fails_closed(self):
        w = self.trusted_witness()
        self.a._conn.execute(
            "CREATE TEMP TRIGGER fail_commit BEFORE UPDATE ON checkpoint "
            "BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.a.revoke("cap")
        # Trusted witness advanced but DB did not: safety-first hard failure.
        with self.assertRaises(CheckpointRejected):
            self.a.export_checkpoint()
        self.a.close()
        with self.assertRaises(CheckpointRejected):
            DurablePolicy(self.path, GKEY, CKEY, checkpoint_witness=w)

    def test_external_witness_two_connections_single_authorization(self):
        w = self.trusted_witness()
        b = DurablePolicy(self.path, GKEY, CKEY, checkpoint_witness=w)
        try:
            with ThreadPoolExecutor(2) as pool:
                results = list(pool.map(
                    lambda p: p.authorize(self.request, now=100), (self.a, b)))
            self.assertEqual(sorted(results), ["ALLOW_POLICY_ONLY", "DENY"])
            self.assertEqual(self.a.checkpoint_stamp(), w.read())
        finally:
            b.close()

if __name__ == "__main__":
    unittest.main()
