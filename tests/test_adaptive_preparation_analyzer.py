"""
Tests de la détection adaptative des périodes de préparation.
"""

import unittest
from datetime import datetime, timedelta

from src.performance import (
    AdaptivePreparationAnalyzer,
    CompetitionEvent,
    LongitudinalActivity,
)


class AdaptivePreparationAnalyzerTests(
    unittest.TestCase
):
    """Vérifie la détection individualisée des préparations."""

    def setUp(self) -> None:
        self.analyzer = AdaptivePreparationAnalyzer()
        self.event_date = datetime.fromisoformat(
            "2026-04-26T09:00:00+02:00"
        )
        self.event = CompetitionEvent(
            event_date=self.event_date,
            title="10 km test",
            distance_km=10,
            outcome="successful",
            outcome_label="Réussie",
        )

    def _run(
        self,
        days_before: int,
        distance_km: float,
        title: str = "Course à pied",
    ) -> LongitudinalActivity:
        return LongitudinalActivity(
            atlas_id=f"run-{days_before}-{title}",
            start_time=(
                self.event_date
                - timedelta(days=days_before)
            ),
            activity_type="running",
            distance_km=distance_km,
            duration_minutes=distance_km * 6,
            average_heart_rate_bpm=135,
            average_speed_kmh=10,
            elevation_gain_m=40,
            title=title,
            data_quality_score=90,
        )

    def test_detects_training_change_instead_of_fixed_window(
        self,
    ) -> None:
        activities = []

        # Historique ancien et peu dense :
        # environ une courte course par semaine.
        for days_before in range(140, 63, -7):
            activities.append(
                self._run(days_before, 5)
            )

        # Préparation structurée commencée environ
        # huit semaines avant la compétition.
        for days_before in range(56, 6, -7):
            activities.extend(
                [
                    self._run(
                        days_before,
                        8,
                    ),
                    self._run(
                        days_before - 2,
                        7,
                        "Séance seuil",
                    ),
                    self._run(
                        days_before - 4,
                        12,
                        "Sortie longue",
                    ),
                ]
            )

        # Semaine d'affûtage.
        activities.append(
            self._run(4, 5)
        )

        result = self.analyzer.detect(
            activities,
            self.event,
        )

        self.assertGreaterEqual(
            result.duration_weeks,
            7.0,
        )
        self.assertLessEqual(
            result.duration_weeks,
            9.5,
        )
        self.assertGreaterEqual(
            result.confidence_score,
            75,
        )
        self.assertFalse(
            result.data_limited
        )
        self.assertTrue(
            result.detection_reasons
        )

    def test_short_history_uses_earliest_available_activity(
        self,
    ) -> None:
        activities = [
            self._run(24, 6),
            self._run(17, 8),
            self._run(10, 10, "Séance tempo"),
            self._run(4, 5),
        ]

        result = self.analyzer.detect(
            activities,
            self.event,
        )

        self.assertEqual(
            result.detected_start_at,
            activities[0].start_time,
        )
        self.assertTrue(
            result.data_limited
        )
        self.assertLess(
            result.confidence_score,
            75,
        )
        self.assertTrue(
            any(
                "historique"
                in reason.lower()
                for reason in result.detection_reasons
            )
        )

    def test_builds_base_specific_and_taper_phases(
        self,
    ) -> None:
        activities = []

        for days_before in range(84, 6, -7):
            activities.extend(
                [
                    self._run(
                        days_before,
                        8,
                    ),
                    self._run(
                        days_before - 2,
                        7,
                        "Séance seuil",
                    ),
                    self._run(
                        days_before - 4,
                        14,
                        "Sortie longue",
                    ),
                ]
            )

        activities.append(
            self._run(4, 5)
        )

        result = self.analyzer.detect(
            activities,
            self.event,
        )

        self.assertEqual(
            [
                phase.phase_name
                for phase in result.phases
            ],
            [
                "base",
                "specific",
                "taper",
            ],
        )
        self.assertTrue(
            all(
                phase.duration_days > 0
                for phase in result.phases
            )
        )
        self.assertEqual(
            result.phases[-1].end_at,
            self.event_date,
        )


if __name__ == "__main__":
    unittest.main()