import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototypes"))

from network_privacy import (
    Endpoint,
    NetworkPlan,
    NetworkPolicy,
    NetworkPrivacyError,
    redacted_network_event,
    validate_network_plan,
)


def local_scan():
    return Endpoint(
        role="chain_scan",
        host="127.0.0.1",
        port=8332,
        route="local",
        encrypted_transport=False,
        authenticated_transport=True,
    )


def tor_broadcast(host="broadcast-hidden.onion", fallback=False):
    return Endpoint(
        role="tx_broadcast",
        host=host,
        port=8333,
        route="tor",
        encrypted_transport=True,
        authenticated_transport=False,
        fallback=fallback,
    )


class NetworkPrivacyTests(unittest.TestCase):
    def test_local_scan_and_tor_broadcast_pass(self):
        evidence = validate_network_plan(
            NetworkPlan((local_scan(), tor_broadcast()))
        )
        self.assertEqual(evidence["result"], "PASS")
        self.assertEqual(evidence["scan_route"], "local")
        self.assertEqual(evidence["broadcast_route"], "tor")

    def test_remote_scan_is_explicit_opt_in(self):
        plan = NetworkPlan(
            (
                Endpoint("chain_scan", "scan.example", 443, "direct", True, True),
                tor_broadcast(),
            )
        )
        with self.assertRaisesRegex(NetworkPrivacyError, "^REMOTE_SCAN_NOT_ALLOWED$"):
            validate_network_plan(plan)

        evidence = validate_network_plan(
            plan,
            NetworkPolicy(allow_remote_scan=True),
        )
        self.assertEqual(evidence["scan_route"], "direct")

    def test_encrypted_direct_broadcast_is_not_treated_as_anonymous(self):
        plan = NetworkPlan(
            (
                local_scan(),
                Endpoint(
                    "tx_broadcast",
                    "peer.example",
                    8333,
                    "direct",
                    encrypted_transport=True,
                    authenticated_transport=False,
                ),
            )
        )
        with self.assertRaisesRegex(NetworkPrivacyError, "^PRIVATE_BROADCAST_REQUIRED$"):
            validate_network_plan(plan)

    def test_direct_fallback_fails_closed(self):
        plan = NetworkPlan(
            (
                local_scan(),
                tor_broadcast(),
                Endpoint(
                    "tx_broadcast",
                    "fallback.example",
                    8333,
                    "direct",
                    encrypted_transport=True,
                    fallback=True,
                ),
            )
        )
        with self.assertRaisesRegex(NetworkPrivacyError, "^DIRECT_FALLBACK_FORBIDDEN$"):
            validate_network_plan(plan)

    def test_direct_fallback_requires_explicit_policy(self):
        plan = NetworkPlan(
            (
                local_scan(),
                tor_broadcast(),
                Endpoint(
                    "tx_broadcast",
                    "fallback.example",
                    8333,
                    "direct",
                    encrypted_transport=True,
                    fallback=True,
                ),
            )
        )
        evidence = validate_network_plan(
            plan,
            NetworkPolicy(allow_direct_fallback=True),
        )
        self.assertTrue(evidence["direct_fallback_present"])

    def test_async_payjoin_requires_ohttp(self):
        direct_directory = Endpoint(
            "payjoin_directory",
            "directory.example",
            443,
            "direct",
            encrypted_transport=True,
            authenticated_transport=True,
        )
        plan = NetworkPlan((local_scan(), tor_broadcast(), direct_directory))

        with self.assertRaisesRegex(
            NetworkPrivacyError, "^ASYNC_PAYJOIN_REQUIRES_OHTTP$"
        ):
            validate_network_plan(plan, NetworkPolicy(async_payjoin=True))

        ohttp_directory = Endpoint(
            "payjoin_directory",
            "relay.example",
            443,
            "ohttp",
            encrypted_transport=True,
            authenticated_transport=True,
        )
        evidence = validate_network_plan(
            NetworkPlan((local_scan(), tor_broadcast(), ohttp_directory)),
            NetworkPolicy(async_payjoin=True),
        )
        self.assertEqual(evidence["payjoin_route"], "ohttp")

    def test_public_endpoint_cannot_collapse_wallet_roles(self):
        shared_scan = Endpoint(
            "chain_scan",
            "shared.example",
            443,
            "tor",
            encrypted_transport=True,
        )
        shared_broadcast = Endpoint(
            "tx_broadcast",
            "shared.example",
            443,
            "tor",
            encrypted_transport=True,
        )
        plan = NetworkPlan((shared_scan, shared_broadcast))
        with self.assertRaisesRegex(NetworkPrivacyError, "^PUBLIC_ROLE_REUSE$"):
            validate_network_plan(
                plan,
                NetworkPolicy(
                    allow_remote_scan=True,
                    require_private_broadcast=True,
                ),
            )

    def test_nonlocal_route_cannot_point_to_loopback(self):
        bad = NetworkPlan(
            (
                local_scan(),
                Endpoint("tx_broadcast", "127.0.0.1", 9050, "tor", True),
            )
        )
        with self.assertRaisesRegex(NetworkPrivacyError, "^NONLOCAL_ROUTE_LOOPBACK$"):
            validate_network_plan(bad)

    def test_redacted_telemetry_contains_no_endpoint_identity(self):
        evidence = validate_network_plan(
            NetworkPlan((local_scan(), tor_broadcast("very-secret-service.onion")))
        )
        event = redacted_network_event(evidence)
        rendered = repr(event)
        for value in (
            "127.0.0.1",
            "8332",
            "very-secret-service.onion",
            "8333",
        ):
            self.assertNotIn(value, rendered)

    def test_missing_primary_roles_fail_closed(self):
        with self.assertRaisesRegex(NetworkPrivacyError, "^TX_BROADCAST_MISSING$"):
            validate_network_plan(NetworkPlan((local_scan(),)))


if __name__ == "__main__":
    unittest.main()
