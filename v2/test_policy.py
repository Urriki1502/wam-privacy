"""V2-01 acceptance: local capability, provenance, replay and denial vectors."""
from dataclasses import asdict, replace
import json
import unittest

from policy import ConsentIssuer, ConsentReceipt, Grant, PolicyAuthority

GKEY = b"grant-key-32-bytes-for-fixture!!!!"
CKEY = b"consent-key-32-bytes-for-fixture!!"


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.authority = PolicyAuthority(GKEY, CKEY)
        self.consent_issuer = ConsentIssuer(CKEY)
        self.grant = Grant("cap-1", "scanner", "SCAN", "account1", "outpoint-1",
                           "regtest", "recognize", 1000, "session1")
        self.authority.issue_local_grant(self.grant)
        self.request = {k: v for k, v in asdict(self.grant).items() if k != "single_use"}

    def check(self, request=None, *, now=100, consent=None, authority=None):
        return (authority or self.authority).authorize(
            self.request if request is None else request, now=now, consent=consent
        )

    def test_allow_is_policy_only_not_signing(self):
        self.assertEqual(self.check(), "ALLOW_POLICY_ONLY")

    def test_unprovisioned_grant_denied(self):
        self.assertEqual(self.check({**self.request, "capability_id": "attacker"}), "DENY")

    def test_unknown_role_action_and_version(self):
        for field, value in (("actor_role", "unknown"), ("action", "SIGN"),
                             ("policy_version", 3)):
            with self.subTest(field=field):
                self.assertEqual(self.check({**self.request, field: value}), "DENY")

    def test_scanner_cannot_sign(self):
        self.assertEqual(self.check({**self.request, "actor_role": "signer",
                                     "action": "SIGN"}), "DENY")

    def test_viewer_auditor_cannot_sign(self):
        for role in ("viewer", "auditor"):
            self.assertEqual(self.check({**self.request, "actor_role": role,
                                         "action": "SIGN"}), "DENY")

    def test_cross_account_network_resource_purpose_session(self):
        for field, value in (("account_scope", "account2"),
                             ("network_id", "testnet"),
                             ("resource_scope", "outpoint-2"),
                             ("purpose", "export"),
                             ("session_id", "session2")):
            with self.subTest(field=field):
                self.assertEqual(self.check({**self.request, field: value}), "DENY")

    def test_expired(self):
        self.assertEqual(self.check(now=1000), "DENY")

    def test_revoked(self):
        self.authority.revoke("cap-1")
        self.assertEqual(self.check(), "DENY")

    def test_duplicate_or_forged_local_issue(self):
        with self.assertRaises(ValueError):
            self.authority.issue_local_grant(self.grant)
        with self.assertRaises(ValueError):
            self.authority.issue_local_grant(replace(self.grant, actor_role="auditor"))

    def test_single_use_replay_after_completion(self):
        grant = replace(self.grant, capability_id="once", single_use=True)
        self.authority.issue_local_grant(grant)
        request = {k: v for k, v in asdict(grant).items() if k != "single_use"}
        self.assertEqual(self.check(request), "ALLOW_POLICY_ONLY")
        self.assertEqual(self.check(request), "DENY")

    def test_single_use_persists_after_restart(self):
        grant = replace(self.grant, capability_id="once", single_use=True)
        self.authority.issue_local_grant(grant)
        request = {k: v for k, v in asdict(grant).items() if k != "single_use"}
        self.assertEqual(self.check(request), "ALLOW_POLICY_ONLY")
        restored = PolicyAuthority.restore(self.authority.snapshot(), GKEY, CKEY)
        self.assertEqual(self.check(request, authority=restored), "DENY")

    def test_revocation_persists_after_restart(self):
        self.authority.revoke("cap-1")
        restored = PolicyAuthority.restore(self.authority.snapshot(), GKEY, CKEY)
        self.assertEqual(self.check(authority=restored), "DENY")

    def test_clock_rollback_and_checkpoint(self):
        self.assertEqual(self.check(now=500), "ALLOW_POLICY_ONLY")
        self.assertEqual(self.check(now=499), "DENY")
        restored = PolicyAuthority.restore(self.authority.snapshot(), GKEY, CKEY)
        self.assertEqual(self.check(now=499, authority=restored), "DENY")
        self.assertEqual(self.check(now=501, authority=restored), "ALLOW_POLICY_ONLY")

    def test_snapshot_tamper_rejected(self):
        s = json.loads(self.authority.snapshot())
        s["state"]["grants"]["cap-1"]["grant"]["action"] = "SIGN"
        with self.assertRaises(ValueError):
            PolicyAuthority.restore(json.dumps(s), GKEY, CKEY)

    def test_snapshot_wrong_authentication_key_rejected(self):
        with self.assertRaises(ValueError):
            PolicyAuthority.restore(self.authority.snapshot(), b"X" * 32, CKEY)

    def test_malformed_request_and_unknown_fields(self):
        for req in (None, [], "bad", {}, {**self.request, "extra": "yes"},
                    {k: v for k, v in self.request.items() if k != "purpose"}):
            with self.subTest(req=repr(req)):
                self.assertEqual(self.check(req if req is not None else []), "DENY")

    def test_long_wildcard_and_numeric_type(self):
        for field, value in (("purpose", "x" * 257), ("purpose", ""),
                             ("account_scope", "*"), ("resource_scope", "all"),
                             ("expires_at", True), ("policy_version", True),
                             ("expires_at", -1)):
            with self.subTest(field=field):
                self.assertEqual(self.check({**self.request, field: value}), "DENY")
        self.assertEqual(self.check(now=True), "DENY")

    def _disclosure(self):
        g = Grant("cap-disclose", "discloser", "DISCLOSE", "account1",
                  "outpoint-9", "regtest", "invoice-2026", 1000,
                  "session2", single_use=False)
        self.authority.issue_local_grant(g)
        return {k: v for k, v in asdict(g).items() if k != "single_use"}

    def test_disclose_without_credential_rejected(self):
        self.assertEqual(self.check(self._disclosure()), "DENY")

    def test_trusted_ui_consent_is_scoped(self):
        request = self._disclosure()
        receipt = self.consent_issuer.issue_after_user_confirmation(request, expires_at=300)
        self.assertEqual(self.check(request, now=101, consent=receipt), "ALLOW_POLICY_ONLY")
        self.assertEqual(self.check(request, now=102, consent=receipt), "DENY")

    def test_consent_forged_wrong_issuer_rejected(self):
        req = self._disclosure()
        fake = ConsentIssuer(b"Z" * 32).issue_after_user_confirmation(req, expires_at=500)
        self.assertEqual(self.check(req, consent=fake), "DENY")

    def test_consent_tamper_rejected(self):
        req = self._disclosure()
        good = self.consent_issuer.issue_after_user_confirmation(req, expires_at=500)
        forged = replace(good, expires_at=600)
        self.assertEqual(self.check(req, consent=forged), "DENY")

    def test_consent_cross_resource_rejected(self):
        request = self._disclosure()
        receipt = self.consent_issuer.issue_after_user_confirmation(request, expires_at=500)
        other = {**request, "resource_scope": "outpoint-10"}
        self.assertEqual(self.check(other, consent=receipt), "DENY")

    def test_expired_consent_rejected(self):
        request = self._disclosure()
        receipt = self.consent_issuer.issue_after_user_confirmation(request, expires_at=100)
        self.assertEqual(self.check(request, now=100, consent=receipt), "DENY")

    def test_consent_replay_after_restart(self):
        req = self._disclosure()
        receipt = self.consent_issuer.issue_after_user_confirmation(req, expires_at=500)
        self.assertEqual(self.check(req, now=100, consent=receipt), "ALLOW_POLICY_ONLY")
        restored = PolicyAuthority.restore(self.authority.snapshot(), GKEY, CKEY)
        self.assertEqual(self.check(req, now=101, consent=receipt, authority=restored), "DENY")

    def test_nonascii_consent_tokens_fail_closed(self):
        req = self._disclosure()
        good = self.consent_issuer.issue_after_user_confirmation(req, expires_at=500)
        for field, malformed in (("mac", "é" * 64),
                                 ("request_digest", "é" * 64),
                                 ("nonce", "é" * 32)):
            with self.subTest(field=field):
                self.assertEqual(self.check(req, consent=replace(good, **{field: malformed})),
                                 "DENY")

    def test_extra_consent_on_scan_rejected(self):
        req = self._disclosure()
        receipt = self.consent_issuer.issue_after_user_confirmation(req, expires_at=500)
        self.assertEqual(self.check(consent=receipt), "DENY")

    def test_bounded_invalid_snapshot(self):
        with self.assertRaises(ValueError):
            PolicyAuthority.restore("x" * 1_000_001, GKEY, CKEY)

    def test_no_external_permission_from_policy(self):
        for role, action in (("signer", "SIGN"), ("auditor", "AUDIT"),
                             ("broadcaster", "BROADCAST"), ("viewer", "VIEW")):
            g = Grant("cap-" + role, role, action, "account1", "outpoint-1",
                      "regtest", "purpose", 1000, "session-2")
            self.authority.issue_local_grant(g)
            request = {k: v for k, v in asdict(g).items() if k != "single_use"}
            self.assertEqual(self.check(request), "ALLOW_POLICY_ONLY")


if __name__ == "__main__":
    unittest.main()
