"""
Tests de l'analyseur des préparations de compétition.
"""

import unittest
from datetime import datetime, timedelta

from src.performance import (
    CompetitionEvent,
    CompetitionPreparationAnalyzer,
    LongitudinalActivity,
)


class CompetitionPreparationAnalyzerTests(
    unittest.TestCase
):
    """Vérifie les fenêtres et comparaisons."""

    def setUp(self) -> None:
        self.analyzer = (
            CompetitionPreparationAnalyzer()
        )
        self.event_date = datetime.fromisoformat(
            "2026-04-26T09:00:00+02:00"
        )

    def _run(
        self,
        days_before: int,
        distance_km: float,
        title: str = "Dourges Course à pied",
        event_date: datetime | None = None,
    ) -> LongitudinalActivity:
        reference_date = (
            event_date or self.event_date
        )

        return LongitudinalActivity(
            atlas_id=f"run-{reference_date.date()}-{days_before}",
            start_time=(
                reference_date
                - timedelta(days=days_before)
            ),
            activity_type="running",
            distance_km=distance_km,
            duration_minutes=distance_km * 6,
            average_heart_rate_bpm=135,
            average_speed_kmh=10,
            elevation_gain_m=50,
            title=title,
            data_quality_score=90,
        )

    def _event(
        self,
        event_date: datetime | None = None,
        outcome: str = "successful",
        heat_level: str | None = None,
    ) -> CompetitionEvent:
        return CompetitionEvent(
            event_date=(
                event_date or self.event_date
            ),
            title="Compétition test",
            distance_km=10,
            outcome=outcome,
            outcome_label=outcome,
            heat_level=heat_level,
        )

    def test_builds_twelve_eight_four_and_one_week_windows(
        self,
    ) -> None:
        activities = [
            self._run(80, 8),
            self._run(50, 10),
            self._run(20, 12),
            self._run(5, 5),
        ]

        result = self.analyzer.analyse_event(
            activities,
            self._event(),
        )

        self.assertEqual(
            result.twelve_week_window
            .running_activity_count,
            4,
        )
        self.assertEqual(
            result.eight_week_window
            .running_activity_count,
            3,
        )
        self.assertEqual(
            result.four_week_window
            .running_activity_count,
            2,
        )
        self.assertEqual(
            result.final_week_window
            .running_activity_count,
            1,
        )

    def test_classifies_sessions_and_taper(
        self,
    ) -> None:
        activities = [
            self._run(
                27,
                10,
                "Dourges Course à pied",
            ),
            self._run(
                20,
                10,
                "Dourges - Seuil",
            ),
            self._run(
                13,
                10,
                "Dourges - VO2 max",
            ),
            self._run(
                5,
                5,
                "Dourges - Tempo",
            ),
            self._run(
                10,
                15,
                "Dourges - Longue course",
            ),
        ]

        result = self.analyzer.analyse_event(
            activities,
            self._event(),
        )

        self.assertEqual(
            result.four_week_window
            .threshold_session_count,
            1,
        )
        self.assertEqual(
            result.four_week_window
            .vo2_session_count,
            1,
        )
        self.assertEqual(
            result.four_week_window
            .tempo_session_count,
            1,
        )
        self.assertEqual(
            result.four_week_window
            .long_run_count,
            1,
        )
        self.assertEqual(
            result.taper
            .final_week_running_distance_km,
            5,
        )
        self.assertEqual(
            result.taper
            .previous_three_week_average_km,
            15,
        )
        self.assertEqual(
            result.taper.volume_change_percent,
            -66.7,
        )
        self.assertEqual(
            result.taper.days_since_last_run,
            5,
        )

    def test_compares_success_and_heat_related_failure(
        self,
    ) -> None:
        successful_date = self.event_date
        failed_date = datetime.fromisoformat(
            "2026-06-21T09:00:00+02:00"
        )

        activities = [
            self._run(
                20,
                12,
                "Dourges - Seuil",
                successful_date,
            ),
            self._run(
                10,
                15,
                "Dourges - Longue course",
                successful_date,
            ),
            self._run(
                5,
                6,
                "Dourges Course à pied",
                successful_date,
            ),
            self._run(
                20,
                12,
                "Dourges - Seuil",
                failed_date,
            ),
            self._run(
                10,
                15,
                "Dourges - Longue course",
                failed_date,
            ),
            self._run(
                5,
                6,
                "Dourges Course à pied",
                failed_date,
            ),
        ]

        comparison = self.analyzer.compare(
            activities,
            [
                self._event(
                    successful_date,
                    outcome="successful",
                ),
                self._event(
                    failed_date,
                    outcome="failed",
                    heat_level="high",
                ),
            ],
        )

        self.assertEqual(
            len(comparison.analyses),
            2,
        )
        self.assertTrue(
            any(
                "forte chaleur"
                in factor.lower()
                for factor
                in comparison.failure_risk_factors
            )
        )
        self.assertTrue(
            comparison.conclusions
        )


if __name__ == "__main__":
    unittest.main()