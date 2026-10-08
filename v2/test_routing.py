"""Deterministic offline NET-001..004 V2-03 acceptance fixtures."""
from dataclasses import asdict, replace
import json
import unittest

from routing import (
    MAX_ENDPOINTS, DecisionEvent, Endpoint, RoutePolicy, SyntheticTrace,
    compare_synthetic_exposures, observe_synthetic_trace,
    select_broadcast_route,
)

TXID = "ab" * 32
REQ = {"action": "BROADCAST", "network_id": "regtest", "txid": TXID}


def ep(name, role="BROADCAST", transport="TOR", provider="relay-a",
       credential="broadcast-creds", available=True):
    return Endpoint(name, provider, role, transport, credential, available)


class NetworkPolicyTests(unittest.TestCase):
    def setUp(self):
        self.private = RoutePolicy("regtest")
        self.routes = (
            ep("rpc-a", role="SCAN_RPC", provider="rpc-operator",
               credential="scan-creds"),
            ep("private-tor"),
        )

    def choose(self, routes=None, policy=None, request=None):
        return select_broadcast_route(
            REQ if request is None else request,
            self.private if policy is None else policy,
            self.routes if routes is None else routes,
        )

    def test_private_route_available_selected(self):
        d, event = self.choose()
        self.assertEqual(d.status, "SELECTED_POLICY_ONLY")
        self.assertEqual(d.transport, "TOR")
        self.assertEqual(event.code, "ROUTE_POLICY_SELECTED")

    def test_net001_private_route_outage_no_cleartext_fallback(self):
        routes = (replace(self.routes[1], available=False), ep(
            "direct", transport="DIRECT", provider="direct-operator",
            credential="direct-creds"))
        d, event = self.choose(routes)
        self.assertEqual((d.status, d.endpoint_id, d.transport), ("DENY", None, None))
        self.assertEqual(event.code, "ROUTE_DENIED")

    def test_net001_private_routes_both_down(self):
        routes = (ep("tor", available=False),
                  ep("i2p", transport="I2P", available=False),
                  ep("clearnet", transport="DIRECT"))
        self.assertEqual(self.choose(routes)[0].status, "DENY")

    def test_public_direct_requires_explicit_opt_in(self):
        direct = (ep("clear", transport="DIRECT"),)
        self.assertEqual(self.choose(direct)[0].status, "DENY")
        explicit = RoutePolicy("regtest", privacy_required=False,
                               allow_direct=True, permitted_transports=("DIRECT",))
        d, _ = self.choose(direct, explicit)
        self.assertEqual(d.transport, "DIRECT")
        self.assertIn("DIRECT_ORIGIN_METADATA_EXPOSED", d.risk_codes)

    def test_no_silent_direct_on_invalid_policy(self):
        invalid = RoutePolicy("regtest", privacy_required=True, allow_direct=True,
                              permitted_transports=("DIRECT",))
        self.assertEqual(self.choose((ep("clear", transport="DIRECT"),), invalid)[0].status,
                         "DENY")

    def test_no_auto_direct_even_when_undemanding_user(self):
        policy = RoutePolicy("regtest", privacy_required=False)
        self.assertEqual(self.choose((ep("clear", transport="DIRECT"),), policy)[0].status,
                         "DENY")

    def test_net002_provider_shared_default_denied(self):
        routes = (ep("scan", role="SCAN_RPC", provider="same", credential="scan"),
                  ep("tor", provider="same", credential="broadcast"))
        self.assertEqual(self.choose(routes)[0].status, "DENY")

    def test_net002_explicit_warning_instead_of_implied_isolation(self):
        routes = (ep("scan", role="SCAN_RPC", provider="same", credential="scan"),
                  ep("tor", provider="same", credential="broadcast"))
        policy = replace(self.private, shared_provider_mode="WARN")
        d, _ = self.choose(routes, policy)
        self.assertEqual(d.status, "SELECTED_POLICY_ONLY")
        self.assertEqual(d.risk_codes, ("CROSS_ROLE_PROVIDER_CORRELATION",))

    def test_cross_role_credentials_never_shared_even_in_warn_mode(self):
        routes = (ep("scan", role="SCAN_RPC", provider="scan",
                     credential="same-creds"),
                  ep("tor", provider="tor-provider", credential="same-creds"))
        policy = replace(self.private, shared_provider_mode="WARN")
        self.assertEqual(self.choose(routes, policy)[0].status, "DENY")

    def test_net003_broadcast_refuses_seed_view_credentials(self):
        for payload in (
            {**REQ, "seed": "secret"},
            {**REQ, "incoming_view_key": "private"},
            {**REQ, "scanner_database": {"full": "wallet"}},
            {**REQ, "account_scope": "my-wallet"},
            {**REQ, "raw_tx": b"mock bytes"},
        ):
            with self.subTest(keys=list(payload)):
                self.assertEqual(self.choose(request=payload)[0].status, "DENY")

    def test_unknown_role_action_rejected(self):
        self.assertEqual(self.choose(request={**REQ, "action": "SIGN"})[0].status,
                         "DENY")
        routes = (ep("endpoint", role="SIGN"),)
        self.assertEqual(self.choose(routes)[0].status, "DENY")

    def test_wrong_network_fails_closed(self):
        self.assertEqual(self.choose(request={**REQ, "network_id": "mainnet"})[0].status,
                         "DENY")

    def test_missing_txid_or_malformed_values(self):
        for value in (None, True, 12, "Z" * 64, "ab" * 31, "é" * 64):
            with self.subTest(value=repr(value)):
                self.assertEqual(self.choose(request={**REQ, "txid": value})[0].status,
                                 "DENY")
        self.assertEqual(self.choose(request={})[0].status, "DENY")

    def test_random_route_order_deterministic(self):
        a = ep("tor-b")
        b = ep("tor-a")
        c = ep("i2p", transport="I2P")
        one = self.choose((a, b, c))[0]
        two = self.choose((c, b, a))[0]
        self.assertEqual(one.endpoint_id, "tor-a")
        self.assertEqual(two.endpoint_id, "tor-a")

    def test_max_endpoints_bounded(self):
        routes = tuple(ep(f"route-{i}") for i in range(MAX_ENDPOINTS + 1))
        self.assertEqual(self.choose(routes)[0].status, "DENY")

    def test_duplicate_endpoints_rejected(self):
        self.assertEqual(self.choose((ep("dup"), ep("dup")))[0].status, "DENY")

    def test_bool_and_unknown_transport_rejected(self):
        self.assertEqual(self.choose((ep("x", available=1),))[0].status, "DENY")
        self.assertEqual(self.choose((ep("x", transport="OHTTP"),))[0].status, "DENY")
        self.assertEqual(self.choose(policy=replace(
            self.private, shared_provider_mode="SKIP"))[0].status, "DENY")

    def test_decision_event_never_contains_secrets_metadata(self):
        selected, event = self.choose()
        denied, failure = self.choose(request={**REQ, "seed": "test secret"})
        self.assertEqual(denied.status, "DENY")
        for e in (event, failure):
            self.assertIsInstance(e, DecisionEvent)
            audit = json.dumps(asdict(e))
            for sensitive in ("txid", TXID, "source_ip", "relay-a", "rpc-operator",
                              "broadcast-creds", "seed", "scan-creds"):
                self.assertNotIn(sensitive, audit)

    def test_policy_only_never_performs_consensus_validation(self):
        d, _ = self.choose()
        self.assertEqual(d.status, "SELECTED_POLICY_ONLY")
        self.assertFalse(hasattr(d, "valid_block"))
        self.assertFalse(hasattr(d, "valid_proof"))
        self.assertFalse(hasattr(d, "has_signed"))

    def test_net004_first_hop_can_still_see_origin_and_timing(self):
        trace = SyntheticTrace("192.0.2.17", 124000, "TOR", "BROADCAST", TXID, 30)
        view = observe_synthetic_trace("first_hop", trace)
        self.assertIn("source_ip", view.visible_fields)
        self.assertIn("timestamp_ms", view.visible_fields)
        self.assertNotIn("txid", view.visible_fields)
        self.assertEqual(view.anonymity_claim, "NOT_ESTABLISHED")

    def test_net004_network_observers_and_residual_linkability(self):
        trace = SyntheticTrace("192.0.2.17", 124000, "TOR", "BROADCAST", TXID, 30)
        for observer in ("rpc_provider", "broadcast_peer", "chain_observer",
                         "global_observer"):
            with self.subTest(observer=observer):
                view = observe_synthetic_trace(observer, trace)
                self.assertTrue(view.residual_risks)
                self.assertEqual(view.anonymity_claim, "NOT_ESTABLISHED")
        self.assertIn("txid", observe_synthetic_trace(
            "chain_observer", trace).visible_fields)
        self.assertIn("source_ip", observe_synthetic_trace(
            "global_observer", trace).visible_fields)

    def test_public_comparison_contains_no_synthetic_identifiers(self):
        a = SyntheticTrace("192.0.2.17", 124000, "TOR", "BROADCAST", TXID, 30)
        b = replace(a, transport="I2P", timestamp_ms=124001)
        report = compare_synthetic_exposures("first_hop", a, b)
        raw = json.dumps(report)
        self.assertNotIn("192.0.2.17", raw)
        self.assertNotIn(TXID, raw)
        self.assertIn("NOT_ESTABLISHED", raw)

    def test_bad_trace_denied_no_info_leak(self):
        tr = SyntheticTrace("192.0.2.17", 124000, "TOR", "BROADCAST", TXID, 30)
        for wrong in (replace(tr, timestamp_ms=True),
                      replace(tr, block_height=-1),
                      replace(tr, txid="z" * 64),
                      replace(tr, transport="CLEARNET"),
                      replace(tr, source_ip="é" * 300)):
            self.assertIsNone(observe_synthetic_trace("first_hop", wrong))
        self.assertIsNone(observe_synthetic_trace("attacker", tr))

    def test_empty_tuple_and_oversized_endpoint_id(self):
        self.assertEqual(self.choose(())[0].status, "DENY")
        self.assertEqual(self.choose((ep("x"*129),))[0].status, "DENY")


if __name__ == "__main__":
    unittest.main()
