"""Actual pinned A/B composition tests with process death and trusted receipts."""
import concurrent.futures
from dataclasses import asdict, replace
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from policy import Grant, FIELDS
from prototypes.signer_abstraction.model import Approval, PaymentIntent, SignRequest, TransactionOutput
from prototypes.signer_abstraction.provider import FixtureSigner, ProviderError
from v2.sec001_research.durable_policy import DurablePolicy, CheckpointRejected
from v2.sec002_research.journal import PersistentSignerGate
from v2.sec003_research.coordinator import DurableResearchBridge, RecoveryBlocked

KEY, CONSENT = b"g" * 32, b"c" * 32


def inputs():
    request = SignRequest("ab"*32, "regtest", "cd"*32, 1,
                          (TransactionOutput("fixture", 10, "payment"),), 1)
    approval = Approval((PaymentIntent("fixture", 10),), 1)
    grant = Grant("cap", "signer", "SIGN", "account", request.request_id,
                  "regtest", "pay", 100, "session", single_use=True)
    capability = {k: asdict(grant)[k] for k in FIELDS}
    return capability, request, approval, grant


class CountSigner(FixtureSigner):
    def __init__(self, directory, *, crash=False):
        super().__init__()
        self.directory, self.crash = str(directory), crash

    def sign(self, request):
        with open(Path(self.directory)/"calls", "ab", buffering=0) as handle:
            handle.write(b"call\n")
            os.fsync(handle.fileno())
        result = super().sign(request)
        if self.crash:
            os._exit(73)
        return result


def compose(directory, *, provision=False, fault=None, provider_crash=False):
    directory = Path(directory)
    authority = DurablePolicy(directory/"policy.db", KEY, CONSENT, provision=provision)
    gate = PersistentSignerGate(CountSigner(directory, crash=provider_crash),
                                directory/"signer.db", signer_identity="fixture-A")
    bridge = DurableResearchBridge(authority, gate, directory/"intent.db",
                                   account_scope="account", provision=provision, fault=fault)
    return bridge


def crash_worker(directory, stage):
    def fault(point):
        if point == stage:
            os._exit(73)
    bridge = compose(directory, fault=fault, provider_crash=stage == "PROVIDER")
    capability, request, approval, _ = inputs()
    bridge.sign(capability, request, approval, now=1)


def parallel_worker(directory):
    bridge = compose(directory)
    try:
        capability, request, approval, _ = inputs()
        return bridge.sign(capability, request, approval, now=1).envelope
    except RecoveryBlocked as exc:
        return str(exc)
    finally:
        bridge.authority.close()


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        bridge = compose(self.directory, provision=True)
        bridge.authority.issue_local_grant(inputs()[3])
        bridge.authority.close()

    def calls(self):
        path = self.directory/"calls"
        return len(path.read_bytes().splitlines()) if path.exists() else 0

    def attempt(self, **kw):
        bridge = compose(self.directory)
        try:
            capability, request, approval, _ = inputs()
            return bridge.sign(capability, request, approval, **({"now": 1} | kw))
        finally:
            bridge.authority.close()

    def test_real_restart_completed_idempotence(self):
        first = self.attempt()
        self.assertEqual(self.attempt(), first)
        self.assertEqual(self.calls(), 1)

    def test_process_crash_every_commit_cut_blocks_uncertain_retry(self):
        # Use independent durable participant stores for every cut.
        for stage in ("PREPARED", "POLICY_COMMITTED", "POLICY_SPENT",
                      "SIGNING", "PROVIDER", "SIGNER_COMPLETE", "COMPLETE"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                bridge = compose(directory, provision=True)
                bridge.authority.issue_local_grant(inputs()[3])
                old_checkpoint = bridge.authority.export_checkpoint()
                bridge.authority.close()
                process = multiprocessing.Process(target=crash_worker, args=(directory, stage))
                process.start()
                process.join(20)
                if process.is_alive():
                    process.terminate()
                    process.join()
                    self.fail("crash worker timeout")
                self.assertEqual(process.exitcode, 73)
                bridge = compose(directory)
                try:
                    capability, request, approval, _ = inputs()
                    if stage == "COMPLETE":
                        bridge.sign(capability, request, approval, now=1)
                    else:
                        with self.assertRaisesRegex(RecoveryBlocked, "INTENT_UNCERTAIN"):
                            bridge.sign(capability, request, approval, now=1)
                    if stage != "PREPARED":
                        with self.assertRaises(CheckpointRejected):
                            bridge.authority.validate_checkpoint(old_checkpoint)
                        state = __import__("json").loads(
                            bridge.authority.export_checkpoint()["snapshot"])["state"]
                        self.assertIn("cap", state["used"])
                    calls = Path(directory)/"calls"
                    actual = len(calls.read_bytes().splitlines()) if calls.exists() else 0
                    self.assertEqual(actual, int(stage in
                                     ("PROVIDER", "SIGNER_COMPLETE", "COMPLETE")))
                finally:
                    bridge.authority.close()

    def test_concurrent_processes_invoke_provider_once(self):
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(parallel_worker, [self.directory] * 12))
        self.assertEqual(self.calls(), 1)
        self.assertTrue(any(isinstance(value, bytes) for value in outcomes))
        self.assertTrue(all(isinstance(value, bytes) or value == "INTENT_UNCERTAIN"
                            for value in outcomes))

    def test_modified_approval_binding_never_replays(self):
        self.attempt()
        bridge = compose(self.directory)
        try:
            capability, request, approval, _ = inputs()
            with self.assertRaisesRegex(RecoveryBlocked, "REQUEST_BINDING_MISMATCH"):
                bridge.sign(capability, request, replace(approval, max_fee_atoms=2), now=1)
        finally:
            bridge.authority.close()
        self.assertEqual(self.calls(), 1)

    def test_revoked_cache_delivery_denied(self):
        self.attempt()
        bridge = compose(self.directory)
        bridge.authority.revoke("cap")
        bridge.authority.close()
        with self.assertRaisesRegex(RecoveryBlocked, "POLICY_RECEIPT_INVALID"):
            self.attempt()
        self.assertEqual(self.calls(), 1)

    def test_expired_cache_delivery_denied(self):
        self.attempt()
        with self.assertRaisesRegex(RecoveryBlocked, "POLICY_RECEIPT_INVALID"):
            self.attempt(now=100)
        self.assertEqual(self.calls(), 1)

    def test_deleted_signer_receipt_blocks_cache(self):
        self.attempt()
        with sqlite3.connect(self.directory/"signer.db") as db:
            db.execute("DELETE FROM requests")
        with self.assertRaisesRegex(RecoveryBlocked, "SIGNER_RECEIPT_INVALID"):
            self.attempt()
        self.assertEqual(self.calls(), 1)

    def test_policy_rollback_against_coordinator_receipt_blocks(self):
        old = (self.directory/"policy.db").read_bytes()
        self.attempt()
        (self.directory/"policy.db").write_bytes(old)
        with self.assertRaisesRegex(RecoveryBlocked, "POLICY_RECEIPT_INVALID"):
            self.attempt()
        self.assertEqual(self.calls(), 1)

    def test_missing_coordinator_is_not_reprovisioned(self):
        self.attempt()
        (self.directory/"intent.db").unlink()
        with self.assertRaises(sqlite3.DatabaseError):
            self.attempt()
        self.assertEqual(self.calls(), 1)

    def test_mutated_caller_mapping_does_not_change_authorized_binding(self):
        capability, request, approval, _ = inputs()
        def fault(stage):
            if stage == "PREPARED":
                capability["purpose"] = "attacker-mutated"
        bridge = compose(self.directory, fault=fault)
        try:
            bridge.sign(capability, request, approval, now=1)
        finally:
            bridge.authority.close()
        self.assertEqual(self.calls(), 1)
        self.assertEqual(self.attempt().request_id, request.request_id)

    def test_unrelated_generation_cannot_fake_consumption_receipt(self):
        self.attempt()
        # Corrupt one trusted participant to emulate independently mixed stores;
        # a greater global generation alone must not satisfy receipt binding.
        bridge = compose(self.directory)
        original = bridge.authority.export_checkpoint()
        bridge.authority.close()
        import json
        from policy import PolicyAuthority
        authority = PolicyAuthority.restore(original["snapshot"], KEY, CONSENT)
        authority._used.clear()
        with sqlite3.connect(self.directory/"policy.db") as db:
            db.execute("UPDATE checkpoint SET generation=?,snapshot=?",
                       (original["generation"] + 10, authority.snapshot()))
        with self.assertRaisesRegex(RecoveryBlocked, "POLICY_RECEIPT_INVALID"):
            self.attempt()
        self.assertEqual(self.calls(), 1)

    def test_fresh_multiuse_grant_rejected_before_provider(self):
        bridge = compose(self.directory)
        try:
            capability, request, approval, grant = inputs()
            grant = replace(grant, capability_id="multi", single_use=False)
            bridge.authority.issue_local_grant(grant)
            capability["capability_id"] = "multi"
            with self.assertRaisesRegex(RecoveryBlocked, "SINGLE_USE_REQUIRED"):
                bridge.sign(capability, request, approval, now=1)
        finally:
            bridge.authority.close()
        self.assertEqual(self.calls(), 0)


if __name__ == "__main__":
    unittest.main()
