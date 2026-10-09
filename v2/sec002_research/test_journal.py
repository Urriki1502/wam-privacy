import concurrent.futures
from dataclasses import replace
import multiprocessing
import os
from pathlib import Path
import tempfile
import sqlite3
import unittest
from prototypes.signer_abstraction.model import Approval, PaymentIntent, SignRequest, TransactionOutput
from prototypes.signer_abstraction.provider import FixtureSigner, ProviderError
from v2.sec002_research.journal import PersistentSignerGate

def inputs():
    return (SignRequest("ab"*32,"regtest","cd"*32,1,(TransactionOutput("fixture",10,"payment"),),1),
            Approval((PaymentIntent("fixture",10),),1))

def worker(path):
    try:
        class CountSigner(FixtureSigner):
            def sign(self, request):
                with open(str(path)+".calls", "ab", buffering=0) as log:log.write(b"call\\n")
                return super().sign(request)
        result = PersistentSignerGate(CountSigner(),path).sign(*inputs())
        return result.envelope
    except ProviderError as exc:
        return str(exc)

def crash_worker(path):
    class CrashSigner(FixtureSigner):
        def sign(self, request):
            super().sign(request)
            os._exit(73)
    PersistentSignerGate(CrashSigner(),path).sign(*inputs())

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"journal.db"
        PersistentSignerGate(FixtureSigner(), self.path, provision=True)
    def test_restart_idempotence(self):
        provider=FixtureSigner()
        result=PersistentSignerGate(provider,self.path).sign(*inputs())
        after=FixtureSigner()
        self.assertEqual(PersistentSignerGate(after,self.path).sign(*inputs()),result)
        self.assertEqual((provider.calls,after.calls),(1,0))
    def test_conflicting_binding(self):
        r,a=inputs()
        PersistentSignerGate(FixtureSigner(),self.path).sign(r,a)
        for changed_r,changed_a in [(replace(r,tx_digest="ef"*32),a),(r,replace(a,max_fee_atoms=2))]:
            with self.assertRaisesRegex(ProviderError,"REQUEST_BINDING_MISMATCH"):
                PersistentSignerGate(FixtureSigner(),self.path).sign(changed_r,changed_a)
    def test_provider_uncertainty_remains_spent(self):
        provider=FixtureSigner(fail=True)
        with self.assertRaisesRegex(ProviderError,"PROVIDER_FAILED"):
            PersistentSignerGate(provider,self.path).sign(*inputs())
        after=FixtureSigner()
        with self.assertRaisesRegex(ProviderError,"REQUEST_PENDING"):
            PersistentSignerGate(after,self.path).sign(*inputs())
        self.assertEqual(after.calls,0)
    def test_crash_after_provider(self):
        p=multiprocessing.Process(target=crash_worker,args=(self.path,))
        p.start();p.join(20)
        self.assertFalse(p.is_alive())
        self.assertEqual(p.exitcode,73)
        after=FixtureSigner()
        with self.assertRaisesRegex(ProviderError,"REQUEST_PENDING"):
            PersistentSignerGate(after,self.path).sign(*inputs())
        self.assertEqual(after.calls,0)
    def test_threads_only_one_provider_call(self):
        provider=FixtureSigner()
        gate=PersistentSignerGate(provider,self.path)
        def attempt(_):
            try:return gate.sign(*inputs()).envelope
            except ProviderError as exc:return str(exc)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results=list(pool.map(attempt,range(24)))
        self.assertEqual(provider.calls,1)
        self.assertTrue(all(isinstance(x,bytes) or x=="REQUEST_PENDING" for x in results))
    def test_process_concurrency(self):
        PersistentSignerGate(FixtureSigner(),self.path)
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(worker,[self.path]*12))
        self.assertEqual(Path(str(self.path)+".calls").read_bytes(),b"call\\n")
        self.assertTrue(any(isinstance(x,bytes) for x in results))
        self.assertTrue(all(isinstance(x,bytes) or x=="REQUEST_PENDING" for x in results))
    def test_hex_alias_idempotence(self):
        r,a=inputs()
        p=FixtureSigner();g=PersistentSignerGate(p,self.path)
        self.assertEqual(g.sign(r,a),g.sign(replace(r,request_id=r.request_id.upper(),tx_digest=r.tx_digest.upper()),a))
        self.assertEqual(p.calls,1)
    def test_corrupt_journal_fails_closed(self):
        self.path.write_bytes(b"corrupt database")
        after=FixtureSigner()
        with self.assertRaises(sqlite3.DatabaseError):
            PersistentSignerGate(after,self.path).sign(*inputs())
        self.assertEqual(after.calls,0)
    def test_signer_identity_binding(self):
        PersistentSignerGate(FixtureSigner(),self.path,signer_identity="fixture-A").sign(*inputs())
        after=FixtureSigner()
        with self.assertRaisesRegex(ProviderError,"REQUEST_BINDING_MISMATCH"):
            PersistentSignerGate(after,self.path,signer_identity="fixture-B").sign(*inputs())
        self.assertEqual(after.calls,0)
    def test_invalid_policy_before_reservation(self):
        r,a=inputs();p=FixtureSigner();g=PersistentSignerGate(p,self.path)
        with self.assertRaisesRegex(ProviderError,"FEE_NOT_APPROVED"):
            g.sign(replace(r,fee_atoms=2),a)
        g.sign(r,a)
        self.assertEqual(p.calls,1)
    def test_frozen_provider_result_failure_stays_pending(self):
        p=FixtureSigner(mismatch=True);g=PersistentSignerGate(p,self.path)
        with self.assertRaisesRegex(ProviderError,"PROVIDER_RESULT_MISMATCH"):g.sign(*inputs())
        with self.assertRaisesRegex(ProviderError,"REQUEST_PENDING"):g.sign(*inputs())
        self.assertEqual(p.calls,1)

    def test_missing_journal_fails_closed_and_does_not_recreate(self):
        self.path.unlink()
        provider=FixtureSigner()
        with self.assertRaisesRegex(ProviderError,"JOURNAL_UNAVAILABLE"):
            PersistentSignerGate(provider,self.path)
        self.assertFalse(self.path.exists())
        self.assertEqual(provider.calls,0)

    def test_deleted_journal_after_success_cannot_reuse_request(self):
        provider=FixtureSigner()
        gate=PersistentSignerGate(provider,self.path)
        gate.sign(*inputs())
        self.path.unlink()
        with self.assertRaisesRegex(ProviderError,"JOURNAL_UNAVAILABLE"):
            gate.sign(*inputs())
        with self.assertRaisesRegex(ProviderError,"JOURNAL_UNAVAILABLE"):
            PersistentSignerGate(FixtureSigner(),self.path)
        self.assertFalse(self.path.exists())
        self.assertEqual(provider.calls,1)

    def test_existing_journal_cannot_be_reprovisioned(self):
        provider=FixtureSigner()
        first=PersistentSignerGate(provider,self.path).sign(*inputs())
        with self.assertRaisesRegex(ProviderError,"JOURNAL_ALREADY_EXISTS"):
            PersistentSignerGate(FixtureSigner(),self.path,provision=True)
        again=FixtureSigner()
        self.assertEqual(PersistentSignerGate(again,self.path).sign(*inputs()),first)
        self.assertEqual(again.calls,0)

    def test_missing_schema_fails_closed_without_bootstrap(self):
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TABLE requests")
        provider=FixtureSigner()
        with self.assertRaises(sqlite3.DatabaseError):
            PersistentSignerGate(provider,self.path)
        self.assertEqual(provider.calls,0)
        with sqlite3.connect(self.path) as db:
            self.assertIsNone(db.execute(
                "SELECT name FROM sqlite_master WHERE name='requests'").fetchone())

if __name__=="__main__":unittest.main()
