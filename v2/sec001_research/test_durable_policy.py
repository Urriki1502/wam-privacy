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

GKEY = b"G" * 32
CKEY = b"C" * 32

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

    def restart(self):
        self.a.close()
        self.a = DurablePolicy(self.path, GKEY, CKEY)

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

if __name__ == "__main__":
    unittest.main()
