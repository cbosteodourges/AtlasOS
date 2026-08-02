"""Tests automatisés du connecteur de démonstration ATLAS OS."""

import unittest

from src.connectors import DemoConnector, NormalizedActivity


class DemoConnectorTests(unittest.TestCase):
    """Vérifie la connexion, l'importation et la normalisation."""

    def setUp(self) -> None:
        self.connector = DemoConnector()

    def test_fetch_requires_connection(self) -> None:
        with self.assertRaises(RuntimeError):
            list(self.connector.fetch_activities())

    def test_normalize_demo_activity(self) -> None:
        self.connector.connect()

        samples = list(self.connector.fetch_activities())
        self.assertEqual(len(samples), 1)

        activity = self.connector.normalize(samples[0])

        self.assertIsInstance(activity, NormalizedActivity)
        self.assertEqual(activity.provider, "demo")
        self.assertEqual(activity.external_id, "demo-run-001")
        self.assertEqual(activity.activity_type, "running")
        self.assertEqual(activity.distance_meters, 10000.0)
        self.assertEqual(activity.duration_seconds, 3600.0)
        self.assertEqual(activity.average_heart_rate_bpm, 152.0)
        self.assertEqual(activity.atlas_id, "demo:demo-run-001")
        self.assertEqual(len(activity.samples), 1)

    def test_activity_can_be_serialized(self) -> None:
        self.connector.connect()
        sample = next(iter(self.connector.fetch_activities()))
        activity = self.connector.normalize(sample)

        serialized = activity.to_dict()

        self.assertEqual(serialized["provider"], "demo")
        self.assertEqual(serialized["external_id"], "demo-run-001")
        self.assertIsInstance(serialized["samples"], list)
        self.assertEqual(
            serialized["samples"][0]["heart_rate_bpm"],
            152.0,
        )


if __name__ == "__main__":
    unittest.main()