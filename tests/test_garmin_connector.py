"""Tests automatisés du connecteur Garmin ATLAS OS."""

import tempfile
import unittest
from datetime import datetime, timezone

from src.connectors import (
    GarminConnector,
    NormalizedActivity,
    RawActivity,
)


class GarminConnectorTests(unittest.TestCase):
    """Vérifie l'importation et la normalisation Garmin."""

    def test_connect_requires_existing_directory(self) -> None:
        connector = GarminConnector(
            "dossier-garmin-inexistant"
        )

        with self.assertRaises(FileNotFoundError):
            connector.connect()

    def test_empty_directory_returns_no_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            connector = GarminConnector(directory)
            connector.connect()

            activities = list(
                connector.fetch_activities()
            )

        self.assertEqual(activities, [])

    def test_normalize_garmin_activity(self) -> None:
        raw_activity = RawActivity(
            provider="garmin",
            external_id="2026-08-02-08-00-00",
            payload={
                "session": {
                    "sport": "running",
                    "start_time": datetime(
                        2026,
                        8,
                        2,
                        6,
                        0,
                        tzinfo=timezone.utc,
                    ),
                    "total_timer_time": 2700.0,
                    "total_elapsed_time": 2800.0,
                    "total_distance": 10000.0,
                    "total_calories": 720,
                    "avg_heart_rate": 154,
                    "max_heart_rate": 176,
                    "enhanced_avg_speed": 3.70,
                    "total_ascent": 82,
                    "training_stress_score": 96.0,
                },
                "device_info": {
                    "garmin_product": "forerunner_255"
                },
                "source_file": "activity.fit",
            },
        )

        connector = GarminConnector(".")
        activity = connector.normalize(raw_activity)

        self.assertIsInstance(activity, NormalizedActivity)
        self.assertEqual(
            activity.atlas_id,
            "garmin:2026-08-02-08-00-00",
        )
        self.assertEqual(activity.activity_type, "running")
        self.assertEqual(activity.duration_seconds, 2700.0)
        self.assertEqual(activity.distance_meters, 10000.0)
        self.assertEqual(activity.calories_kcal, 720.0)
        self.assertEqual(activity.average_heart_rate_bpm, 154.0)
        self.assertEqual(activity.maximum_heart_rate_bpm, 176.0)
        self.assertEqual(activity.average_speed_mps, 3.70)
        self.assertEqual(activity.elevation_gain_m, 82.0)
        self.assertEqual(activity.training_load, 96.0)
        self.assertEqual(
            activity.source_device,
            "forerunner_255",
        )

    def test_build_samples_from_fit_records(self) -> None:
        records = [
            {
                "timestamp": datetime(
                    2026,
                    8,
                    2,
                    6,
                    0,
                    tzinfo=timezone.utc,
                ),
                "heart_rate": 152,
                "enhanced_speed": 3.5,
                "cadence": 168,
                "power": 285,
                "enhanced_altitude": 42.0,
                "position_lat": 2 ** 30,
                "position_long": -(2 ** 30),
            }
        ]

        samples = GarminConnector._build_samples(records)

        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].heart_rate_bpm, 152.0)
        self.assertEqual(samples[0].speed_mps, 3.5)
        self.assertEqual(samples[0].cadence_spm, 168.0)
        self.assertEqual(samples[0].power_watts, 285.0)
        self.assertEqual(samples[0].altitude_m, 42.0)
        self.assertEqual(samples[0].latitude, 90.0)
        self.assertEqual(samples[0].longitude, -90.0)


if __name__ == "__main__":
    unittest.main()