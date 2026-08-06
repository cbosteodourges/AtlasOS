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
                    "sub_sport": "generic",
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
                    "workout_rpe": 40,
                    "workout_feel": 75,
                    "avg_running_cadence": 80,
                    "max_running_cadence": 97,
                    "avg_step_length": 911.6,
                    "avg_vertical_ratio": 9.2,
                    "avg_vertical_oscillation": 82.5,
                    "avg_stance_time": 292.6,
                    "avg_power": 354,
                    "max_power": 765,
                    "normalized_power": 369,
                    "avg_temperature": 31,
                    "min_temperature": 30,
                    "max_temperature": 31,
                    "total_training_effect": 2.9,
                    "total_anaerobic_training_effect": 1.2,
                },
                "device_info": {
                    "garmin_product": "fr255"
                },
                "laps": [{
                    "timestamp": datetime(
                        2026, 8, 2, 6, 10,
                        tzinfo=timezone.utc,
                    ),
                    "total_distance": 1000.0,
                }],
                "time_in_zones": [{
                    1: "session",
                    "threshold_heart_rate": 161,
                    "time_in_hr_zone": [60.0, 120.0],
                }],
                "workout": [{
                    "wkt_name": "5x1000m récup 2min",
                    "num_valid_steps": 5,
                }],
                "workout_steps": [{
                    "message_index": 0,
                    "duration_type": "time",
                    "duration_time": 600.0,
                    "target_type": "open",
                    "intensity": "warmup",
                }],
                "events": [{
                    "event": "workout",
                    "event_type": "start",
                }],
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
            activity.raw_metadata["workout_rpe_raw"],
            40.0,
        )
        self.assertEqual(
            activity.raw_metadata["perceived_effort"],
            4.0,
        )
        self.assertEqual(
            activity.raw_metadata["workout_feel_raw"],
            75.0,
        )
        self.assertEqual(
            activity.raw_metadata["feeling_score"],
            75.0,
        )
        self.assertEqual(
            activity.raw_metadata["feeling_label"],
            "strong",
        )
        self.assertEqual(
            activity.raw_metadata["average_cadence"],
            160.0,
        )
        self.assertEqual(
            activity.raw_metadata["maximum_cadence"],
            194.0,
        )
        self.assertAlmostEqual(
            activity.raw_metadata["average_stride_length"],
            0.9116,
        )
        self.assertEqual(
            activity.raw_metadata["average_vertical_oscillation"],
            8.25,
        )
        self.assertEqual(
            activity.raw_metadata["average_ground_contact_time"],
            292.6,
        )
        self.assertEqual(
            activity.raw_metadata["normalized_power"],
            369.0,
        )
        self.assertEqual(
            activity.raw_metadata["laps"][0]["timestamp"],
            "2026-08-02T08:10:00+02:00",
        )
        self.assertEqual(
            activity.raw_metadata["time_in_zones"][0]["1"],
            "session",
        )
        self.assertEqual(
            activity.source_device,
            "Garmin Forerunner 255",
        )

        self.assertEqual(
            activity.raw_metadata["workout"][0]["wkt_name"],
            "5x1000m récup 2min",
        )
        self.assertEqual(
            activity.raw_metadata["workout_steps"][0]["intensity"],
            "warmup",
        )
        self.assertEqual(
            activity.raw_metadata["events"][0]["event_type"],
            "start",
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