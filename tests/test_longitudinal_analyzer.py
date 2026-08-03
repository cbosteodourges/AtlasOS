"""
Tests de l'analyseur longitudinal Performance Intelligence v2.
"""

import unittest
from datetime import datetime

from src.performance import (
    LongitudinalActivity,
    LongitudinalPerformanceAnalyzer,
)


class LongitudinalPerformanceAnalyzerTests(
    unittest.TestCase
):
    """Vérifie les calculs de l'analyse longitudinale."""

    def setUp(self) -> None:
        self.analyzer = LongitudinalPerformanceAnalyzer()

    def _activity(
        self,
        activity_id: str,
        date_value: str,
        distance_km: float,
        activity_type: str = "running",
        quality: int = 80,
    ) -> LongitudinalActivity:
        return LongitudinalActivity(
            atlas_id=activity_id,
            start_time=datetime.fromisoformat(
                date_value
            ),
            activity_type=activity_type,
            distance_km=distance_km,
            duration_minutes=distance_km * 6,
            average_heart_rate_bpm=140,
            average_speed_kmh=10,
            elevation_gain_m=50,
            data_quality_score=quality,
        )

    def test_empty_history_is_supported(
        self,
    ) -> None:
        result = self.analyzer.analyse([])

        self.assertEqual(
            result.activity_count,
            0,
        )
        self.assertEqual(
            result.running_activity_count,
            0,
        )
        self.assertIsNone(
            result.first_activity_at
        )
        self.assertTrue(
            result.warnings
        )

    def test_builds_weekly_history_with_zero_week(
        self,
    ) -> None:
        activities = [
            self._activity(
                "run-1",
                "2026-01-05T08:00:00+01:00",
                10,
            ),
            self._activity(
                "run-2",
                "2026-01-06T08:00:00+01:00",
                8,
            ),
            self._activity(
                "bike-1",
                "2026-01-12T08:00:00+01:00",
                30,
                activity_type="cycling",
            ),
            self._activity(
                "run-3",
                "2026-01-19T08:00:00+01:00",
                8,
            ),
        ]

        result = self.analyzer.analyse(
            activities
        )

        self.assertEqual(
            result.activity_count,
            4,
        )
        self.assertEqual(
            result.running_activity_count,
            3,
        )
        self.assertEqual(
            result.total_running_distance_km,
            26,
        )
        self.assertEqual(
            len(result.weekly_summaries),
            3,
        )
        self.assertEqual(
            result.weekly_summaries[0]
            .running_distance_km,
            18,
        )
        self.assertEqual(
            result.weekly_summaries[1]
            .running_distance_km,
            0,
        )
        self.assertEqual(
            result.weekly_summaries[2]
            .running_distance_km,
            8,
        )
        self.assertEqual(
            result.average_running_distance_per_week_km,
            8.7,
        )
        self.assertEqual(
            result.maximum_running_distance_per_week_km,
            18,
        )
        self.assertEqual(
            result.longest_running_activity_km,
            10,
        )
        self.assertEqual(
            result.data_quality_score,
            80,
        )

    def test_compares_recent_and_previous_four_weeks(
        self,
    ) -> None:
        activities = [
            self._activity(
                "previous-1",
                "2026-01-11T08:00:00+01:00",
                10,
            ),
            self._activity(
                "previous-2",
                "2026-01-18T08:00:00+01:00",
                10,
            ),
            self._activity(
                "previous-3",
                "2026-01-25T08:00:00+01:00",
                10,
            ),
            self._activity(
                "previous-4",
                "2026-02-01T08:00:00+01:00",
                10,
            ),
            self._activity(
                "recent-1",
                "2026-02-08T08:00:00+01:00",
                15,
            ),
            self._activity(
                "recent-2",
                "2026-02-15T08:00:00+01:00",
                15,
            ),
            self._activity(
                "recent-3",
                "2026-02-22T08:00:00+01:00",
                15,
            ),
            self._activity(
                "recent-4",
                "2026-03-01T08:00:00+01:00",
                15,
            ),
        ]

        result = self.analyzer.analyse(
            activities
        )

        self.assertEqual(
            result.previous_four_week_distance_km,
            40,
        )
        self.assertEqual(
            result.recent_four_week_distance_km,
            60,
        )
        self.assertEqual(
            result.recent_load_change_percent,
            50,
        )
        self.assertTrue(
            any(
                "quatre dernières semaines"
                in warning
                for warning in result.warnings
            )
        )


if __name__ == "__main__":
    unittest.main()