"""
Tests de l'adaptateur Performance Intelligence v2.
"""

import unittest

from src.connectors import NormalizedActivity
from src.performance import (
    LongitudinalActivityAdapter,
    TrainingActivityAdapter,
)


class LongitudinalActivityAdapterTests(
    unittest.TestCase
):
    """Vérifie la conversion vers le modèle longitudinal."""

    def setUp(self) -> None:
        self.adapter = LongitudinalActivityAdapter()

    def test_adapt_complete_running_activity(
        self,
    ) -> None:
        activity = NormalizedActivity(
            provider="garmin",
            external_id="garmin-test-001",
            activity_type="running",
            start_time="2026-08-02T08:30:00+02:00",
            duration_seconds=2638,
            distance_meters=6552,
            calories_kcal=617,
            average_heart_rate_bpm=134,
            maximum_heart_rate_bpm=159,
            average_speed_mps=2.4837,
            elevation_gain_m=131,
            training_load=82,
            source_device="Garmin Forerunner 255",
            raw_metadata={
                "title": "Course test",
                "average_cadence": 164,
                "maximum_cadence": 181,
                "average_stride_length": 0.92,
                "average_vertical_ratio": 8.7,
                "average_vertical_oscillation": 8.0,
                "average_ground_contact_time": 267,
                "average_power": 326,
                "maximum_power": 512,
                "normalized_power": 341,
                "minimum_temperature": 16,
                "maximum_temperature": 22,
                "minimum_altitude": 34,
                "maximum_altitude": 112,
                "aerobic_training_effect": 3.2,
                "perceived_effort": 4.0,
                "feeling_score": 75.0,
                "feeling_label": "strong",
                "body_battery_consumption": 14,
                "average_respiration_rate": 31,
                "minimum_respiration_rate": 18,
                "maximum_respiration_rate": 42,
            },
        )

        result = self.adapter.adapt(activity)

        self.assertEqual(
            result.atlas_id,
            "garmin:garmin-test-001",
        )
        self.assertEqual(
            result.activity_type,
            "running",
        )
        self.assertAlmostEqual(
            result.distance_km,
            6.552,
        )
        self.assertAlmostEqual(
            result.duration_minutes,
            43.9667,
            places=3,
        )
        self.assertEqual(
            result.average_heart_rate_bpm,
            134,
        )
        self.assertEqual(
            result.dynamics.average_cadence_spm,
            164,
        )
        self.assertEqual(
            result.dynamics.average_power_watts,
            326,
        )
        self.assertEqual(
            result.environment.minimum_temperature_c,
            16,
        )
        self.assertEqual(
            result.recovery.aerobic_training_effect,
            3.2,
        )
        self.assertEqual(
            result.recovery.perceived_effort_1_to_10,
            4.0,
        )
        self.assertEqual(
            result.recovery.feeling_score_0_to_100,
            75.0,
        )
        self.assertEqual(
            result.recovery.feeling_label,
            "strong",
        )
        self.assertEqual(
            result.energy.total_calories_kcal,
            617,
        )
        self.assertEqual(
            result.title,
            "Course test",
        )
        self.assertEqual(
            result.data_quality_score,
            100,
        )

    def test_calculates_pace_and_aerobic_efficiency(
        self,
    ) -> None:
        activity = NormalizedActivity(
            provider="garmin",
            external_id="garmin-test-002",
            activity_type="running",
            start_time="2026-08-01T08:30:00+02:00",
            duration_seconds=3000,
            distance_meters=10000,
            average_heart_rate_bpm=150,
            average_speed_mps=10 / 3,
        )

        result = self.adapter.adapt(activity)

        self.assertEqual(
            result.pace_seconds_per_km,
            300,
        )
        self.assertAlmostEqual(
            result.aerobic_efficiency,
            0.08,
        )

    def test_missing_optional_data_is_supported(
        self,
    ) -> None:
        activity = NormalizedActivity(
            provider="garmin",
            external_id="garmin-test-003",
            activity_type="running",
            start_time="2026-07-30T08:30:00+02:00",
            duration_seconds=1800,
        )

        result = self.adapter.adapt(activity)

        self.assertEqual(
            result.distance_km,
            0,
        )
        self.assertIsNone(
            result.pace_seconds_per_km
        )
        self.assertIsNone(
            result.aerobic_efficiency
        )
        self.assertIsNone(
            result.dynamics.average_cadence_spm
        )
        self.assertLess(
            result.data_quality_score,
            100,
        )


    def test_adapts_longitudinal_to_training_activity(
        self,
    ) -> None:
        activity = NormalizedActivity(
            provider="garmin",
            external_id="garmin-bridge-001",
            activity_type="running",
            start_time="2026-08-02T08:30:00+02:00",
            duration_seconds=2638,
            distance_meters=6552,
            average_heart_rate_bpm=134,
            maximum_heart_rate_bpm=159,
            raw_metadata={
                "title": "Course test",
                "perceived_effort": 4,
            },
        )

        longitudinal = self.adapter.adapt(activity)
        result = TrainingActivityAdapter().adapt(
            longitudinal
        )

        self.assertEqual(
            result.activity_date.isoformat(),
            "2026-08-02",
        )
        self.assertEqual(
            result.activity_type,
            "running",
        )
        self.assertAlmostEqual(
            result.distance_km,
            6.552,
        )
        self.assertEqual(
            result.duration_minutes,
            44,
        )
        self.assertEqual(
            result.average_heart_rate,
            134,
        )
        self.assertEqual(
            result.maximum_heart_rate,
            159,
        )
        self.assertEqual(
            result.perceived_exertion,
            4,
        )
        self.assertEqual(
            result.notes,
            "Course test",
        )


if __name__ == "__main__":
    unittest.main()