"""Tests automatisés du connecteur Strava ATLAS OS."""

import unittest

from src.connectors import (
    NormalizedActivity,
    RawActivity,
    StravaConnector,
)


class StravaConnectorTests(unittest.TestCase):
    """Vérifie la connexion et la normalisation Strava."""

    def test_connect_requires_access_token(self) -> None:
        connector = StravaConnector("")

        with self.assertRaises(ValueError):
            connector.connect()

    def test_fetch_requires_connection(self) -> None:
        connector = StravaConnector("test-token")

        with self.assertRaises(RuntimeError):
            list(connector.fetch_activities())

    def test_normalize_strava_activity(self) -> None:
        connector = StravaConnector("test-token")
        raw_activity = RawActivity(
            provider="strava",
            external_id="123456789",
            payload={
                "id": 123456789,
                "name": "Course du matin",
                "sport_type": "Run",
                "start_date": "2026-08-02T06:00:00Z",
                "moving_time": 2700,
                "elapsed_time": 2800,
                "distance": 10000.0,
                "calories": 720.0,
                "average_heartrate": 154.2,
                "max_heartrate": 176.0,
                "average_speed": 3.70,
                "total_elevation_gain": 82.0,
                "suffer_score": 96.0,
                "device_name": "Garmin Forerunner 255",
                "commute": False,
                "trainer": False,
                "private": False,
            },
        )

        activity = connector.normalize(raw_activity)

        self.assertIsInstance(activity, NormalizedActivity)
        self.assertEqual(activity.atlas_id, "strava:123456789")
        self.assertEqual(activity.activity_type, "run")
        self.assertEqual(activity.duration_seconds, 2700.0)
        self.assertEqual(activity.distance_meters, 10000.0)
        self.assertEqual(activity.average_heart_rate_bpm, 154.2)
        self.assertEqual(activity.maximum_heart_rate_bpm, 176.0)
        self.assertEqual(activity.average_speed_mps, 3.70)
        self.assertEqual(activity.elevation_gain_m, 82.0)
        self.assertEqual(activity.training_load, 96.0)
        self.assertEqual(
            activity.source_device,
            "Garmin Forerunner 255",
        )

    def test_iso_date_is_converted_to_epoch(self) -> None:
        epoch = StravaConnector._to_epoch(
            "1970-01-01T00:00:00Z"
        )

        self.assertEqual(epoch, 0)


if __name__ == "__main__":
    unittest.main()