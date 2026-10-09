"""Defensive adapter tests against actual frozen APIs; synthetic regtest data."""
from dataclasses import asdict
import unittest
from policy import Grant, PolicyAuthority, ConsentIssuer
from disclosure import DisclosureService, LocalWalletFacts, WalletFact, SelectionIssuer
from boundary import LocalConsentBoundary

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.a = PolicyAuthority(b"G"*32, b"C"*32)
        self.g = Grant("g", "discloser", "DISCLOSE", "a", "r", "regtest", "invoice", 1000, "s")
        self.a.issue_local_grant(self.g)
        self.req = asdict(self.g); self.req.pop("single_use")
        self.svc = DisclosureService(self.a, LocalWalletFacts([WalletFact("a","r","regtest","ab"*32,4,2)]), b"F"*32)

    def boundary(self, confirm, clock=lambda:100):
        return LocalConsentBoundary(self.svc, ConsentIssuer(b"C"*32), SelectionIssuer(b"F"*32), confirm, clock)

    def test_cancel_and_truthy_remote_values_deny(self):
        for value in (False, None, 1, "yes", {"confirmed":True}):
            self.assertIsNone(self.boundary(lambda p:value).release(self.req, ("txid",)))

    def test_confirmation_displays_exact_scope_fields_metadata(self):
        prompts = []
        def confirm(prompt):
            prompts.append(prompt)
            return True
        out = self.boundary(confirm).release(self.req, ("txid",))
        self.assertEqual(dict(prompts[0].request), self.req)
        self.assertEqual(prompts[0].selected_fields, ("txid",))
        self.assertEqual(set(prompts[0].exported_metadata), {"network_id","resource_scope","purpose"})
        self.assertEqual(out["facts"], {"txid":"ab"*32})
        self.assertEqual(set(out), {"schema_version","network_id","resource_scope","purpose","facts"})

    def test_no_rpc_confirmation_parameter(self):
        with self.assertRaises(TypeError):
            self.boundary(lambda p:False).release(self.req, ("txid",), confirmed=True)

    def test_request_mutation_during_ui_does_not_change_approved_scope(self):
        original = dict(self.req)
        def confirm(prompt):
            self.req["purpose"] = "changed"
            return True
        out = self.boundary(confirm).release(self.req, ("txid",))
        self.assertEqual(out["purpose"], original["purpose"])

    def test_revoke_during_confirmation_denies(self):
        def confirm(prompt):
            self.a.revoke("g")
            return True
        self.assertIsNone(self.boundary(confirm).release(self.req, ("txid",)))

    def test_invalid_fields_request_and_expired_clock_deny(self):
        b = self.boundary(lambda p:True)
        for fields in ((), ("memo",), ("txid","txid")):
            self.assertIsNone(b.release(self.req, fields))
        self.assertIsNone(b.release({**self.req,"confirmed":True}, ("txid",)))
        self.assertIsNone(self.boundary(lambda p:True, lambda:1000).release(self.req, ("txid",)))
        self.assertIsNone(self.boundary(lambda p:True, lambda:True).release(self.req, ("txid",)))

    def test_ui_failure_denies(self):
        def confirm(prompt):
            raise RuntimeError("local UI unavailable")
        self.assertIsNone(self.boundary(confirm).release(self.req, ("txid",)))

    def test_latest_authenticated_restart_preserves_consent_denial(self):
        c = ConsentIssuer(b"C"*32).issue_after_user_confirmation(self.req, expires_at=200)
        selection = SelectionIssuer(b"F"*32).issue_after_user_confirmation(self.req,c,("txid",),expires_at=200)
        self.assertIsNotNone(self.svc.disclose(self.req,now=100,consent=c,selection=selection)[0])
        restored = PolicyAuthority.restore(self.a.snapshot(),b"G"*32,b"C"*32)
        svc = DisclosureService(restored,LocalWalletFacts([WalletFact("a","r","regtest","ab"*32,4,2)]),b"F"*32)
        self.assertIsNone(svc.disclose(self.req,now=101,consent=c,selection=selection)[0])

if __name__ == "__main__":
    unittest.main()
