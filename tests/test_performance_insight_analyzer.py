"""
Tests de l'analyse comparative Performance Intelligence.
"""

import unittest
from datetime import datetime

from src.performance import (
    LongitudinalActivity,
    PerformanceInsightAnalyzer,
    RecoveryMetrics,
    RunningDynamics,
)


class PerformanceInsightAnalyzerTests(
    unittest.TestCase
):
    """Vérifie les comparaisons et références."""

    def setUp(self) -> None:
        self.analyzer = PerformanceInsightAnalyzer()

    def _run(
        self,
        activity_id: str,
        date_value: str,
        distance_km: float,
        speed_kmh: float,
        heart_rate: float,
        cadence: float = 165,
        stride_length: float = 1.0,
        power: float = 300,
    ) -> LongitudinalActivity:
        duration_minutes = (
            distance_km / speed_kmh * 60
        )

        return LongitudinalActivity(
            atlas_id=activity_id,
            start_time=datetime.fromisoformat(
                date_value
            ),
            activity_type="running",
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            average_heart_rate_bpm=heart_rate,
            average_speed_kmh=speed_kmh,
            dynamics=RunningDynamics(
                average_cadence_spm=cadence,
                average_stride_length_m=stride_length,
                average_power_watts=power,
            ),
            recovery=RecoveryMetrics(
                aerobic_training_effect=3.0,
                body_battery_impact=12,
            ),
            data_quality_score=90,
        )

    def test_empty_history_is_supported(
        self,
    ) -> None:
        result = self.analyzer.analyse([])

        self.assertEqual(
            result.early_window.running_activity_count,
            0,
        )
        self.assertEqual(
            result.recent_window.running_activity_count,
            0,
        )
        self.assertTrue(
            result.warnings
        )

    def test_compares_early_and_recent_windows(
        self,
    ) -> None:
        activities = [
            self._run(
                "early-1",
                "2026-01-01T08:00:00+01:00",
                10,
                10,
                150,
                cadence=164,
                stride_length=0.98,
                power=290,
            ),
            self._run(
                "early-2",
                "2026-01-15T08:00:00+01:00",
                10,
                10,
                150,
                cadence=164,
                stride_length=0.98,
                power=290,
            ),
            self._run(
                "recent-1",
                "2026-04-01T08:00:00+02:00",
                10,
                11,
                145,
                cadence=168,
                stride_length=1.05,
                power=310,
            ),
            self._run(
                "recent-2",
                "2026-04-08T08:00:00+02:00",
                10,
                11,
                145,
                cadence=168,
                stride_length=1.05,
                power=310,
            ),
        ]

        result = self.analyzer.analyse(
            activities
        )

        self.assertEqual(
            result.early_window.running_activity_count,
            2,
        )
        self.assertEqual(
            result.recent_window.running_activity_count,
            2,
        )
        self.assertEqual(
            result.average_speed_change_percent,
            10,
        )
        self.assertGreater(
            result.pace_change_percent or 0,
            0,
        )
        self.assertLess(
            result.average_heart_rate_change_percent or 0,
            0,
        )
        self.assertGreater(
            result.aerobic_efficiency_change_percent or 0,
            0,
        )
        self.assertGreater(
            result.cadence_change_percent or 0,
            0,
        )
        self.assertGreater(
            result.stride_length_change_percent or 0,
            0,
        )

    def test_identifies_distance_benchmarks(
        self,
    ) -> None:
        activities = [
            self._run(
                "run-5k",
                "2026-01-01T08:00:00+01:00",
                5,
                12,
                155,
            ),
            self._run(
                "run-10k",
                "2026-02-01T08:00:00+01:00",
                10,
                11,
                150,
            ),
            self._run(
                "run-half",
                "2026-03-01T08:00:00+01:00",
                21.1,
                10,
                145,
            ),
        ]

        result = self.analyzer.analyse(
            activities
        )
        benchmarks = result.distance_benchmarks

        self.assertEqual(
            len(benchmarks),
            3,
        )
        self.assertEqual(
            benchmarks[0].best_activity_id,
            "run-5k",
        )
        self.assertEqual(
            benchmarks[1].best_activity_id,
            "run-10k",
        )
        self.assertEqual(
            benchmarks[2].best_activity_id,
            "run-half",
        )
        self.assertEqual(
            benchmarks[0].best_pace_seconds_per_km,
            300,
        )
        self.assertEqual(
            benchmarks[2].best_pace_seconds_per_km,
            360,
        )


if __name__ == "__main__":
    unittest.main()