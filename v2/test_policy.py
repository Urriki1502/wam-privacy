import unittest
from dataclasses import asdict
from policy import Grant, authorize


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.grant = Grant("cap1", "scanner", "SCAN", "a", "n1", "regtest",
                           "scan", 1000, "s")
        self.request = asdict(self.grant)
        self.grants = {"cap1": self.grant}

    def check(self, request=None, grants=None, revoked=frozenset(),
              now=100, trusted=True, consent=False):
        return authorize(self.request if request is None else request,
                         self.grants if grants is None else grants,
                         revoked, now, trusted_grants=trusted,
                         user_consented=consent)

    def test_valid_policy_only(self):
        self.assertEqual(self.check(), "ALLOW_POLICY_ONLY")

    def test_untrusted_grant_source(self):
        self.assertEqual(self.check(trusted=False), "DENY")

    def test_unknown_role_action_version(self):
        for key, value in [("actor_role", "unknown"), ("action", "SIGN"),
                           ("policy_version", 3)]:
            with self.subTest(key=key):
                self.assertEqual(self.check({**self.request, key: value}), "DENY")

    def test_no_scan_to_sign(self):
        self.assertEqual(self.check({**self.request, "actor_role": "signer",
                                     "action": "SIGN"}), "DENY")

    def test_account_network_scope(self):
        for key, value in [("account_scope", "b"), ("network_id", "testnet"),
                           ("resource_scope", "n2"), ("purpose", "export"),
                           ("session_id", "other")]:
            with self.subTest(key=key):
                self.assertEqual(self.check({**self.request, key: value}), "DENY")

    def test_expiry(self):
        self.assertEqual(self.check(now=1000), "DENY")

    def test_revocation(self):
        self.assertEqual(self.check(revoked=frozenset({"cap1"})), "DENY")

    def test_missing_extra_or_oversized(self):
        self.assertEqual(self.check({**self.request, "extra": "x"}), "DENY")
        r = dict(self.request)
        del r["purpose"]
        self.assertEqual(self.check(r), "DENY")
        self.assertEqual(self.check({**self.request, "purpose": "x" * 257}), "DENY")

    def test_disclosure_requires_consent(self):
        g = Grant("cap2", "discloser", "DISCLOSE", "a", "n1", "regtest",
                  "audit", 1000, "s")
        r = asdict(g)
        self.assertEqual(self.check(r, {"cap2": g}), "DENY")
        self.assertEqual(self.check(r, {"cap2": g}, consent=True),
                         "ALLOW_POLICY_ONLY")

    def test_no_audit_spend(self):
        self.assertEqual(self.check({**self.request, "actor_role": "auditor",
                                     "action": "SIGN"}), "DENY")

    def test_no_view_spend(self):
        self.assertEqual(self.check({**self.request, "actor_role": "viewer",
                                     "action": "SIGN"}), "DENY")


if __name__ == "__main__":
    unittest.main()
