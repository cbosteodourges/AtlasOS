"""
Tests des empreintes individualisées de séances.
"""

import unittest
from datetime import datetime, timedelta

from src.performance import (
    LongitudinalActivity,
    RecoveryMetrics,
    SessionFingerprintBuilder,
)


class SessionFingerprintBuilderTests(
    unittest.TestCase
):
    """Vérifie la construction et l'agrégation des empreintes."""

    def setUp(self) -> None:
        self.builder = SessionFingerprintBuilder()
        self.start_time = datetime.fromisoformat(
            "2026-04-01T18:00:00+02:00"
        )

    def _activity(
        self,
        title: str,
        distance_km: float,
        duration_minutes: float,
        days_after: int = 0,
        perceived_effort: float | None = 6,
        feeling_score: float | None = 75,
    ) -> LongitudinalActivity:
        return LongitudinalActivity(
            atlas_id=(
                f"activity-{days_after}-{title}"
            ),
            start_time=(
                self.start_time
                + timedelta(days=days_after)
            ),
            activity_type="running",
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            average_heart_rate_bpm=145,
            maximum_heart_rate_bpm=168,
            average_speed_kmh=(
                distance_km
                / duration_minutes
                * 60
            ),
            elevation_gain_m=80,
            training_load=120,
            recovery=RecoveryMetrics(
                perceived_effort_1_to_10=(
                    perceived_effort
                ),
                feeling_score_0_to_100=(
                    feeling_score
                ),
                aerobic_training_effect=3.5,
                anaerobic_training_effect=1.2,
                body_battery_impact=-18,
            ),
            title=title,
            data_quality_score=90,
        )

    def test_classifies_threshold_session(
        self,
    ) -> None:
        fingerprint = self.builder.build(
            self._activity(
                "Dourges - Séance seuil",
                10,
                52,
            )
        )

        self.assertEqual(
            fingerprint.session_type,
            "threshold",
        )
        self.assertGreater(
            fingerprint.intensity_score,
            50,
        )
        self.assertGreater(
            fingerprint.internal_load_score,
            0,
        )
        self.assertGreaterEqual(
            fingerprint.fingerprint_confidence_score,
            80,
        )
        self.assertTrue(
            fingerprint.classification_reasons
        )

    def test_classifies_long_run_before_easy_run(
        self,
    ) -> None:
        fingerprint = self.builder.build(
            self._activity(
                "Course à pied",
                17,
                105,
            )
        )

        self.assertEqual(
            fingerprint.session_type,
            "long_run",
        )

    def test_missing_subjective_data_is_explicit(
        self,
    ) -> None:
        activity = self._activity(
            "Course facile",
            7,
            45,
            perceived_effort=None,
            feeling_score=None,
        )
        activity.training_load = None
        activity.recovery.aerobic_training_effect = None
        activity.recovery.body_battery_impact = None

        fingerprint = self.builder.build(
            activity
        )

        self.assertIn(
            "Effort perçu",
            fingerprint.missing_data,
        )
        self.assertIn(
            "Ressenti",
            fingerprint.missing_data,
        )
        self.assertIsNone(
            fingerprint.immediate_response_score
        )
        self.assertLess(
            fingerprint.fingerprint_confidence_score,
            80,
        )

    def test_builds_learning_by_session_type(
        self,
    ) -> None:
        activities = [
            self._activity(
                "Course facile",
                7,
                45,
                days_after=0,
                perceived_effort=3,
                feeling_score=85,
            ),
            self._activity(
                "Endurance fondamentale",
                8,
                50,
                days_after=2,
                perceived_effort=3,
                feeling_score=88,
            ),
            self._activity(
                "Séance seuil",
                10,
                52,
                days_after=4,
                perceived_effort=7,
                feeling_score=72,
            ),
            self._activity(
                "Séance seuil",
                11,
                56,
                days_after=7,
                perceived_effort=7,
                feeling_score=75,
            ),
        ]

        learning = self.builder.build_learning(
            athlete_id="christophe",
            activities=activities,
        )

        self.assertEqual(
            learning.fingerprint_count,
            4,
        )
        self.assertEqual(
            {
                result.session_type
                for result
                in learning.session_type_effectiveness
            },
            {
                "easy",
                "threshold",
            },
        )
        self.assertGreater(
            learning.global_confidence_score,
            0,
        )
        self.assertTrue(
            learning.conclusions
        )


if __name__ == "__main__":
    unittest.main()