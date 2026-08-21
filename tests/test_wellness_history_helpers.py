"""Tests des jours manquants, baselines et indice Wellness."""

import unittest
from datetime import date

from src.connectors.garmin_wellness import DailyRecoverySnapshot
from tools.atlas_web_server import (
    _atlas_recovery_index,
    _complete_wellness_calendar,
    _personal_baseline,
)


class WellnessHistoryHelpersTests(unittest.TestCase):
    def test_keeps_missing_calendar_days_explicit(self):
        history = [
            {"day": "2026-08-01", "sleep_score": 80},
            {"day": "2026-08-03", "sleep_score": 82},
        ]

        complete = _complete_wellness_calendar(history)

        self.assertEqual(len(complete), 3)
        self.assertFalse(complete[1]["data_present"])
        self.assertIsNone(complete[1]["source"])

    def test_personal_baseline_uses_only_previous_days(self):
        history = [
            {"sleep_score": 70},
            {"sleep_score": 80},
            {"sleep_score": 90},
            {"sleep_score": 100},
        ]

        self.assertEqual(_personal_baseline(history, 3, "sleep_score"), 80)

    def test_training_load_contributes_to_atlas_index(self):
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 8, 5),
            sleep_score=80,
            sleep_recovery_score=75,
            hrv_last_night_ms=50,
            hrv_baseline_lower_ms=45,
            hrv_baseline_upper_ms=55,
            sleep_average_stress=20,
            data_quality_score=100,
        )

        normal = _atlas_recovery_index(
            snapshot, training_load=50, training_load_baseline=50
        )
        high = _atlas_recovery_index(
            snapshot, training_load=150, training_load_baseline=50
        )

        self.assertLess(high["score"], normal["score"])
        self.assertTrue(any(
            item["label"] == "Charge sur 7 jours" for item in high["components"]
        ))


if __name__ == "__main__":
    unittest.main()
