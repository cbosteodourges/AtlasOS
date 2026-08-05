"""
Tests du constructeur de profil sportif adaptatif.
"""

import unittest
from datetime import datetime, timedelta

from src.performance import (
    AthleteProfileBuilder,
    CompetitionEvent,
    LongitudinalActivity,
    PhysiologicalReferences,
)


class AthleteProfileBuilderTests(
    unittest.TestCase
):
    """Vérifie l'adaptation au niveau observé."""

    def setUp(self) -> None:
        self.builder = AthleteProfileBuilder()
        self.start = datetime.fromisoformat(
            "2026-01-05T08:00:00+01:00"
        )

    def _run(
        self,
        week: int,
        day: int,
        distance_km: float,
        title: str = "Course à pied",
    ) -> LongitudinalActivity:
        return LongitudinalActivity(
            atlas_id=f"run-{week}-{day}",
            start_time=(
                self.start
                + timedelta(
                    weeks=week,
                    days=day,
                )
            ),
            activity_type="running",
            distance_km=distance_km,
            duration_minutes=distance_km * 6,
            average_heart_rate_bpm=135,
            average_speed_kmh=10,
            title=title,
            data_quality_score=90,
        )

    def _competitions(
        self,
    ) -> list[CompetitionEvent]:
        return [
            CompetitionEvent(
                event_date=(
                    self.start
                    + timedelta(weeks=12)
                ),
                title="10 km test",
                distance_km=10,
                outcome="successful",
                outcome_label="Réussie",
            ),
            CompetitionEvent(
                event_date=(
                    self.start
                    + timedelta(weeks=20)
                ),
                title="Semi test",
                distance_km=21.1,
                outcome="successful",
                outcome_label="Réussie",
            ),
            CompetitionEvent(
                event_date=(
                    self.start
                    + timedelta(weeks=28)
                ),
                title="Semi difficile",
                distance_km=21.1,
                outcome="failed",
                outcome_label="Ratée",
            ),
        ]

    def test_empty_history_builds_beginner_profile(
        self,
    ) -> None:
        profile = self.builder.build(
            athlete_id="athlete-empty",
            declared_level="beginner",
            activities=[],
        )

        self.assertEqual(
            profile.observed_level,
            "beginner",
        )
        self.assertEqual(
            profile.history_activity_count,
            0,
        )
        self.assertEqual(
            profile.history_duration_weeks,
            0,
        )
        self.assertIn(
            "Aucune course exploitable.",
            profile.limitations,
        )

    def test_builds_competitive_profile_from_history(
        self,
    ) -> None:
        activities = []

        for week in range(30):
            activities.extend(
                [
                    self._run(
                        week,
                        0,
                        8,
                        (
                            "Dourges - Seuil"
                            if week % 3 == 0
                            else "Course à pied"
                        ),
                    ),
                    self._run(
                        week,
                        2,
                        10,
                    ),
                    self._run(
                        week,
                        5,
                        12,
                    ),
                ]
            )

        profile = self.builder.build(
            athlete_id="athlete-competitive",
            declared_level="regular_amateur",
            activities=activities,
            competitions=self._competitions(),
            physiological=PhysiologicalReferences(
                vma_kmh=14,
                vo2_max=51,
                threshold_heart_rate_bpm=160,
            ),
            training_age_years=8,
        )

        self.assertEqual(
            profile.observed_level,
            "competitive",
        )
        self.assertEqual(
            profile.competition_count,
            3,
        )
        self.assertEqual(
            profile.successful_competition_count,
            2,
        )
        self.assertEqual(
            profile.tolerance
            .usual_running_distance_per_week_km,
            30,
        )
        self.assertEqual(
            profile.tolerance
            .usual_running_sessions_per_week,
            3,
        )
        self.assertGreaterEqual(
            profile.profile_confidence_score,
            80,
        )
        self.assertIn(
            "10_km",
            profile.preferred_competition_types,
        )
        self.assertIn(
            "half_marathon",
            profile.preferred_competition_types,
        )

    def test_declared_elite_requires_dense_history(
        self,
    ) -> None:
        activities = []

        for week in range(30):
            for day in range(5):
                activities.append(
                    self._run(
                        week,
                        day,
                        12,
                        (
                            "Séance VO2 max"
                            if day == 1
                            else "Course à pied"
                        ),
                    )
                )

        profile = self.builder.build(
            athlete_id="athlete-elite",
            declared_level="elite",
            activities=activities,
            competitions=self._competitions(),
        )

        self.assertEqual(
            profile.observed_level,
            "high_performance",
        )
        self.assertEqual(
            profile.tolerance
            .usual_running_distance_per_week_km,
            60,
        )
        self.assertEqual(
            profile.tolerance
            .usual_running_sessions_per_week,
            5,
        )


    def test_current_profile_uses_recent_twelve_weeks(
        self,
    ) -> None:
        activities = [
            self._run(
                -104,
                0,
                50,
                "Ancienne sortie",
            )
        ]

        for week in range(12):
            activities.extend(
                [
                    self._run(week, 0, 8),
                    self._run(week, 2, 10),
                    self._run(week, 5, 12),
                ]
            )

        profile = self.builder.build(
            athlete_id="athlete-recent",
            declared_level="regular_amateur",
            activities=activities,
        )

        self.assertGreater(
            profile.history_duration_weeks,
            100,
        )
        self.assertEqual(
            profile.tolerance
            .usual_running_distance_per_week_km,
            30,
        )
        self.assertEqual(
            profile.tolerance
            .usual_running_sessions_per_week,
            3,
        )
        self.assertEqual(
            profile.tolerance
            .maximum_observed_weekly_distance_km,
            50,
        )
        self.assertEqual(
            profile.observed_level,
            "regular_amateur",
        )


if __name__ == "__main__":
    unittest.main()