"""V2-02: FLOW-003..006 and bounded selective disclosure fixtures."""
from dataclasses import replace, asdict
import json
import unittest

from disclosure import (
    AuditEvent, DisclosureService, LocalWalletFacts, MAX_DISCLOSURE_BYTES,
    MAX_RECORDS, SelectionIssuer, WalletFact,
)
from policy import ConsentIssuer, Grant, PolicyAuthority

GRANT_KEY = b"G" * 32
CONSENT_KEY = b"C" * 32
FIELDS_KEY = b"F" * 32
TXID = "ab" * 32


class SelectiveDisclosureTests(unittest.TestCase):
    def setUp(self):
        self.authority = PolicyAuthority(GRANT_KEY, CONSENT_KEY)
        self.ui_consent = ConsentIssuer(CONSENT_KEY)
        self.ui_selection = SelectionIssuer(FIELDS_KEY)
        self.grant = Grant("grant-a", "discloser", "DISCLOSE", "account-a",
                           "outpoint-a", "regtest", "invoice-A", 1000, "session-a")
        self.authority.issue_local_grant(self.grant)
        self.req = {key: value for key, value in asdict(self.grant).items()
                    if key != "single_use"}
        self.wallet = LocalWalletFacts([
            WalletFact("account-a", "outpoint-a", "regtest", TXID, 25000, 420),
            WalletFact("account-b", "outpoint-b", "regtest", "ef" * 32, 11, 421),
        ])
        self.service = DisclosureService(self.authority, self.wallet, FIELDS_KEY)

    def receipts(self, fields=("txid",)):
        consent = self.ui_consent.issue_after_user_confirmation(self.req, expires_at=600)
        selection = self.ui_selection.issue_after_user_confirmation(
            self.req, consent, fields, expires_at=600
        )
        return consent, selection

    def release(self, req=None, consent=None, selection=None, *, now=100, service=None):
        return (service or self.service).disclose(
            req if req is not None else self.req, now=now,
            consent=consent, selection=selection,
        )

    def test_only_selected_txid_no_history_or_amount(self):
        c, s = self.receipts()
        payload, event = self.release(consent=c, selection=s)
        self.assertEqual(payload["facts"], {"txid": TXID})
        self.assertEqual(event.code, "DISCLOSE_RELEASED")
        encoded = json.dumps(payload)
        for secret in ("account-a", "account-b", "session-a", "seed",
                       "memo", "recipient", "25000", "421"):
            self.assertNotIn(secret, encoded)

    def test_authorized_multiple_fields(self):
        c, s = self.receipts(("amount_atoms", "block_height", "txid"))
        payload, event = self.release(consent=c, selection=s)
        self.assertEqual(set(payload["facts"]), {"amount_atoms", "block_height", "txid"})
        self.assertLessEqual(len(json.dumps(payload).encode()), MAX_DISCLOSURE_BYTES)

    def test_reject_no_ui_consent(self):
        self.assertEqual(self.release()[0], None)

    def test_reject_no_field_selection(self):
        c, _ = self.receipts()
        self.assertIsNone(self.release(consent=c)[0])

    def test_reject_field_tamper(self):
        c, s = self.receipts()
        s2 = replace(s, approved_fields=("amount_atoms",))
        self.assertIsNone(self.release(consent=c, selection=s2)[0])

    def test_reject_unapproved_data_fields(self):
        c = self.ui_consent.issue_after_user_confirmation(self.req, expires_at=600)
        for fields in (("memo",), ("spend_secret",), ("txid", "memo"),
                       (), ("txid", "txid"), ("txid", "block_height", "amount_atoms", "extra"),
                       ("txid", "amount_atoms")):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    self.ui_selection.issue_after_user_confirmation(
                        self.req, c, fields, expires_at=600
                    )

    def test_cross_account_network_resource_purpose_rejected(self):
        c, s = self.receipts()
        for field, value in (("account_scope", "account-b"),
                             ("network_id", "testnet"),
                             ("resource_scope", "outpoint-b"),
                             ("purpose", "other-invoice"),
                             ("session_id", "session-b")):
            with self.subTest(field=field):
                req = {**self.req, field: value}
                self.assertIsNone(self.release(req, c, s)[0])

    def test_wrong_selection_key_rejected(self):
        c, s = self.receipts()
        forged = SelectionIssuer(b"Z" * 32).issue_after_user_confirmation(
            self.req, c, ("txid",), expires_at=600
        )
        self.assertIsNone(self.release(consent=c, selection=forged)[0])

    def test_consent_replay_denied(self):
        c, s = self.receipts()
        self.assertIsNotNone(self.release(consent=c, selection=s)[0])
        self.assertIsNone(self.release(consent=c, selection=s, now=101)[0])

    def test_old_field_authorization_not_reusable_with_new_consent(self):
        c, s = self.receipts()
        c2 = self.ui_consent.issue_after_user_confirmation(self.req, expires_at=600)
        self.assertIsNone(self.release(consent=c2, selection=s)[0])

    def test_expired_selection(self):
        c, s = self.receipts()
        self.assertIsNone(self.release(consent=c, selection=replace(s, expires_at=100), now=100)[0])

    def test_expired_policy_grant(self):
        c, s = self.receipts()
        self.assertIsNone(self.release(consent=c, selection=s, now=1000)[0])

    def test_revoke_before_disclose(self):
        c, s = self.receipts()
        self.authority.revoke("grant-a")
        self.assertIsNone(self.release(consent=c, selection=s)[0])

    def test_restart_does_not_reenable_consent(self):
        c, s = self.receipts()
        self.assertIsNotNone(self.release(consent=c, selection=s)[0])
        restored = PolicyAuthority.restore(self.authority.snapshot(), GRANT_KEY, CONSENT_KEY)
        svc = DisclosureService(restored, self.wallet, FIELDS_KEY)
        self.assertIsNone(self.release(consent=c, selection=s, service=svc, now=101)[0])

    def test_no_wallet_record(self):
        c, s = self.receipts()
        svc = DisclosureService(self.authority, LocalWalletFacts([]), FIELDS_KEY)
        self.assertIsNone(self.release(consent=c, selection=s, service=svc)[0])

    def test_wrong_local_record_scope(self):
        c, s = self.receipts()
        wallet = LocalWalletFacts([WalletFact("account-b", "outpoint-a", "regtest",
                                             TXID, 25000, 420)])
        svc = DisclosureService(self.authority, wallet, FIELDS_KEY)
        self.assertIsNone(self.release(consent=c, selection=s, service=svc)[0])

    def test_wallet_record_validation(self):
        with self.assertRaises(ValueError):
            LocalWalletFacts([WalletFact("account-a", "outpoint-a", "regtest",
                                         "not-txid", 25000, 420)])
        with self.assertRaises(ValueError):
            LocalWalletFacts([WalletFact("account-a", "outpoint-a", "regtest",
                                         TXID, True, 420)])
        with self.assertRaises(ValueError):
            LocalWalletFacts([WalletFact("account-a", "outpoint-a", "regtest",
                                         TXID, 25000, 420)] * 2)

    def test_bounded_record_count(self):
        with self.assertRaises(ValueError):
            LocalWalletFacts([
                WalletFact("account", f"outpoint-{i}", "regtest", TXID, 10, 42)
                for i in range(MAX_RECORDS + 1)
            ])

    def test_audit_allow_and_deny_fixed_no_sensitive_data(self):
        c, s = self.receipts()
        success, allowed = self.release(consent=c, selection=s)
        failure, denied = self.release(consent=c, selection=s, now=101)
        self.assertIsNone(failure)
        self.assertIsNotNone(success)
        for event in (allowed, denied):
            self.assertIsInstance(event, AuditEvent)
            encoded = json.dumps(asdict(event))
            self.assertLess(len(encoded), 120)
            for secret in ("account-a", "outpoint-a", "invoice-A", TXID,
                           "session-a", "25000", "memo", "recipient", "seed"):
                self.assertNotIn(secret, encoded)

    def test_disclosure_is_not_signing_or_audit_permission(self):
        c, s = self.receipts()
        payload, _ = self.release(consent=c, selection=s)
        self.assertNotIn("signature", payload)
        self.assertNotIn("capability_id", payload)
        self.assertNotIn("spend_authority", payload)

    def test_malformed_selection_and_request(self):
        c, s = self.receipts()
        for val in (None, [], {}, "wrong"):
            with self.subTest(val=repr(val)):
                self.assertIsNone(self.release(consent=c, selection=val)[0])
        self.assertIsNone(self.release(req={**self.req, "extra": "x"}, consent=c, selection=s)[0])

    def test_constant_size_projection(self):
        c, s = self.receipts(("amount_atoms", "block_height", "txid"))
        payload, _ = self.release(consent=c, selection=s)
        self.assertLess(len(json.dumps(payload).encode()), MAX_DISCLOSURE_BYTES)


if __name__ == "__main__":
    unittest.main()
