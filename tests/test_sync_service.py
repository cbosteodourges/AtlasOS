"""Tests automatisés du service de synchronisation ATLAS OS."""

import unittest

from src.connectors import (
    ActivitySyncService,
    ConnectorRegistry,
    DemoConnector,
    NormalizedActivity,
)


class ActivitySyncServiceTests(unittest.TestCase):
    """Vérifie la chaîne complète de synchronisation."""

    def setUp(self) -> None:
        self.registry = ConnectorRegistry()
        self.connector = DemoConnector()
        self.registry.register(self.connector)
        self.service = ActivitySyncService(self.registry)

    def test_synchronize_demo_provider(self) -> None:
        activities = self.service.synchronize("demo")

        self.assertTrue(self.connector.connected)
        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], NormalizedActivity)
        self.assertEqual(
            activities[0].atlas_id,
            "demo:demo-run-001",
        )

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.service.synchronize("garmin")


if __name__ == "__main__":
    unittest.main()