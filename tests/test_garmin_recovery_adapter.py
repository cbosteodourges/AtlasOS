"""
Tests de l’adaptation Garmin Wellness vers la physiologie.
"""

import unittest
from datetime import date, datetime, timezone

from src.connectors.garmin_wellness import (
    DailyRecoverySnapshot,
)
from src.physiology.garmin_recovery_adapter import (
    GarminRecoveryAdapter,
)


class GarminRecoveryAdapterTests(unittest.TestCase):
    """Vérifie la personnalisation des données de récupération."""

    def setUp(self) -> None:
        self.adapter = GarminRecoveryAdapter()

    def test_builds_physiology_input_from_garmin(
        self,
    ) -> None:
        history = [
            DailyRecoverySnapshot(
                day=date(2026, 8, 3),
                hrv_last_night_ms=46.0,
                resting_heart_rate_bpm=47.0,
            ),
            DailyRecoverySnapshot(
                day=date(2026, 8, 4),
                hrv_last_night_ms=50.0,
                resting_heart_rate_bpm=49.0,
            ),
        ]
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 8, 5),
            hrv_last_night_ms=44.0,
            hrv_weekly_average_ms=48.0,
            resting_heart_rate_bpm=46.0,
            sleep_score=81,
            sleep_quality_score=77,
            sleep_average_stress=20.14,
            sleep_levels=[
                {
                    "timestamp": datetime(
                        2026, 8, 4, 22, 30,
                        tzinfo=timezone.utc,
                    ),
                    "sleep_level": "light",
                },
                {
                    "timestamp": datetime(
                        2026, 8, 5, 6, 30,
                        tzinfo=timezone.utc,
                    ),
                    "sleep_level": "rem",
                },
            ],
        )

        result = self.adapter.build_input(
            snapshot,
            history,
            pain_0_10=2,
            acute_load_7d=420,
            chronic_load_28d=390,
            vo2max=51,
            vo2max_baseline=50,
        )

        self.assertEqual(result.hrv_ms, 44.0)
        self.assertEqual(result.hrv_baseline_ms, 48.0)
        self.assertEqual(result.resting_hr_bpm, 46.0)
        self.assertEqual(
            result.resting_hr_baseline_bpm,
            48.0,
        )
        self.assertEqual(result.sleep_hours, 8.0)
        self.assertEqual(result.sleep_quality_0_100, 77)
        self.assertEqual(result.stress_0_10, 2.01)
        self.assertEqual(result.pain_0_10, 2)
        self.assertEqual(result.acute_load_7d, 420)
        self.assertEqual(result.chronic_load_28d, 390)

    def test_uses_personal_hrv_history_as_fallback(
        self,
    ) -> None:
        history = [
            DailyRecoverySnapshot(
                day=date(2026, 8, 2),
                hrv_last_night_ms=40.0,
            ),
            DailyRecoverySnapshot(
                day=date(2026, 8, 3),
                hrv_last_night_ms=50.0,
            ),
            DailyRecoverySnapshot(
                day=date(2026, 8, 4),
                hrv_last_night_ms=60.0,
            ),
        ]
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 8, 5),
            hrv_last_night_ms=48.0,
        )

        result = self.adapter.build_input(
            snapshot,
            history,
        )

        self.assertEqual(result.hrv_baseline_ms, 50.0)

    def test_missing_optional_data_remains_supported(
        self,
    ) -> None:
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 8, 5),
        )

        result = self.adapter.build_input(snapshot)

        self.assertIsNone(result.hrv_ms)
        self.assertIsNone(result.hrv_baseline_ms)
        self.assertIsNone(result.resting_hr_bpm)
        self.assertIsNone(
            result.resting_hr_baseline_bpm
        )
        self.assertIsNone(result.sleep_hours)
        self.assertIsNone(result.sleep_quality_0_100)
        self.assertIsNone(result.stress_0_10)


if __name__ == "__main__":
    unittest.main()