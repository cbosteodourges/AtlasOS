"""Tests de personnalisation du programme FIT + Wellness."""

import unittest

from src.performance.athlete_profile import AthleteProfile
from src.training.training_history_personalizer import (
    TrainingHistoryPersonalizer,
)


class TrainingHistoryPersonalizerTests(unittest.TestCase):
    """Vérifie la traduction de l'historique en décisions."""

    def setUp(self) -> None:
        self.personalizer = TrainingHistoryPersonalizer()

    @staticmethod
    def _activity(
        session_type: str,
        response: float,
        recovery: float,
        confidence: int = 90,
    ) -> dict:
        return {
            "session_type": session_type,
            "response_24h": response,
            "recovered_within_hours": recovery,
            "confidence_score": confidence,
            "automatic_learning_allowed": True,
        }

    def test_builds_protocol_tolerances_and_limits_load(self) -> None:
        activities = []

        for _ in range(8):
            activities.append(
                self._activity(
                    "sprint_acceleration",
                    -0.5,
                    29,
                )
            )
            activities.append(
                self._activity("z2", 2.0, 32)
            )
            activities.append(
                self._activity("sv2", -6.0, 35)
            )
            activities.append(
                self._activity("road", -1.0, 28)
            )

        result = self.personalizer.build({
            "acute_chronic_load_ratio": 1.41,
            "activities": activities,
        })

        self.assertGreater(
            result.session_tolerance_scores["hill_sprints"],
            result.session_tolerance_scores[
                "mixed_threshold_vo2"
            ],
        )
        self.assertEqual(
            result.cycling_sessions_per_week,
            1,
        )
        self.assertEqual(
            result.maximum_weekly_progression_percent,
            5.0,
        )
        self.assertEqual(
            result.recovery_days_after_intensity,
            2.0,
        )
        self.assertEqual(
            result.learned_response_count,
            32,
        )

    def test_ignores_unreliable_activities(self) -> None:
        result = self.personalizer.build({
            "activities": [{
                "session_type": "vma",
                "response_24h": 10,
                "recovered_within_hours": 12,
                "confidence_score": 20,
                "automatic_learning_allowed": False,
            }],
        })

        self.assertEqual(
            result.learned_response_count,
            0,
        )
        self.assertNotIn(
            "vma",
            result.session_tolerance_scores,
        )
        self.assertEqual(
            result.cycling_sessions_per_week,
            0,
        )

    def test_applies_learning_to_athlete_profile(self) -> None:
        profile = AthleteProfile(
            athlete_id="athlete-test",
            declared_level="intermediate",
            observed_level="intermediate",
        )
        personalization = self.personalizer.build({
            "acute_chronic_load_ratio": 1.20,
            "activities": [
                self._activity("vma", -4.0, 36)
                for _ in range(8)
            ],
        })

        returned = self.personalizer.apply(
            profile,
            personalization,
        )

        self.assertIs(returned, profile)
        self.assertEqual(
            profile.tolerance.learned_response_count,
            8,
        )
        self.assertIn(
            "triangular_vo2",
            profile.tolerance.session_type_tolerance_scores,
        )
        self.assertEqual(
            profile.tolerance.usual_recovery_days_after_intensity,
            2.0,
        )
        self.assertEqual(
            profile.tolerance.recent_load_change_percent,
            20.0,
        )


if __name__ == "__main__":
    unittest.main()