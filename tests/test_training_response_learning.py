"""
Tests de l’apprentissage après séance à 24–72 heures.
"""

import unittest
from datetime import date

from src.training.response_learning import (
    TrainingResponseLearningEngine,
    TrainingResponseObservation,
    TrainingResponseOutcome,
)
from src.training.session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class TrainingResponseLearningEngineTests(unittest.TestCase):
    """Vérifie la classification de la réponse réelle."""

    def setUp(self) -> None:
        self.engine = TrainingResponseLearningEngine()
        self.workout = AdaptiveWorkout(
            workout_id="threshold-2026-08-08",
            workout_date=date(2026, 8, 8),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="Séance au seuil",
            objective="Développer le SV2.",
            priority=WorkoutPriority.KEY,
            blocks=[
                TrainingBlock(
                    name="Séance complète",
                    block_type=BlockType.WORK,
                    duration_minutes=50,
                )
            ],
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=72,
                biomechanical_load_0_100=58,
                recovery_min_hours=36,
                recovery_max_hours=48,
            ),
        )

    @staticmethod
    def observation(
        hours: int,
        *,
        recovery: float,
        atlas_index: float,
        fatigue: float,
        soreness: float,
        pain: float,
        rpe: float = 7,
        illness: bool = False,
    ) -> TrainingResponseObservation:
        return TrainingResponseObservation(
            workout_id="threshold-2026-08-08",
            hours_after_session=hours,
            recovery_score=recovery,
            atlas_index_score=atlas_index,
            fatigue_0_10=fatigue,
            muscle_soreness_0_10=soreness,
            pain_0_10=pain,
            illness_symptoms=illness,
            actual_rpe_0_10=rpe,
        )

    def test_learns_from_positive_response(
        self,
    ) -> None:
        observations = [
            self.observation(
                24,
                recovery=66,
                atlas_index=67,
                fatigue=4,
                soreness=3,
                pain=2,
            ),
            self.observation(
                48,
                recovery=72,
                atlas_index=73,
                fatigue=2,
                soreness=2,
                pain=1,
            ),
        ]

        result = self.engine.analyze(
            self.workout,
            observations,
            pre_session_recovery_score=69,
            pre_session_atlas_index_score=69,
            pre_session_pain_0_10=2,
        )

        self.assertEqual(
            result.outcome,
            TrainingResponseOutcome.POSITIVE,
        )
        self.assertEqual(result.next_load_factor, 1.05)
        self.assertEqual(
            result.physiological_tolerance_delta,
            2,
        )
        self.assertEqual(
            result.biomechanical_tolerance_delta,
            2,
        )
        self.assertTrue(result.usable_for_learning)

    def test_detects_delayed_recovery(
        self,
    ) -> None:
        observations = [
            self.observation(
                24,
                recovery=58,
                atlas_index=60,
                fatigue=6,
                soreness=6,
                pain=3,
            ),
            self.observation(
                48,
                recovery=55,
                atlas_index=57,
                fatigue=7,
                soreness=7,
                pain=3,
            ),
        ]

        result = self.engine.analyze(
            self.workout,
            observations,
            pre_session_recovery_score=69,
            pre_session_atlas_index_score=69,
            pre_session_pain_0_10=2,
        )

        self.assertEqual(
            result.outcome,
            TrainingResponseOutcome.DELAYED,
        )
        self.assertEqual(result.next_load_factor, 0.85)
        self.assertTrue(result.usable_for_learning)

    def test_detects_adverse_pain_response(
        self,
    ) -> None:
        observations = [
            self.observation(
                24,
                recovery=55,
                atlas_index=50,
                fatigue=6,
                soreness=6,
                pain=7,
            )
        ]

        result = self.engine.analyze(
            self.workout,
            observations,
            pre_session_recovery_score=69,
            pre_session_atlas_index_score=69,
            pre_session_pain_0_10=2,
        )

        self.assertEqual(
            result.outcome,
            TrainingResponseOutcome.ADVERSE,
        )
        self.assertEqual(result.next_load_factor, 0.65)
        self.assertTrue(result.alerts)

    def test_accepts_response_within_expected_range(
        self,
    ) -> None:
        observations = [
            self.observation(
                24,
                recovery=64,
                atlas_index=65,
                fatigue=5,
                soreness=4,
                pain=2,
            ),
            self.observation(
                48,
                recovery=65,
                atlas_index=66,
                fatigue=4,
                soreness=4,
                pain=2,
            ),
        ]

        result = self.engine.analyze(
            self.workout,
            observations,
            pre_session_recovery_score=69,
            pre_session_atlas_index_score=69,
            pre_session_pain_0_10=2,
        )

        self.assertEqual(
            result.outcome,
            TrainingResponseOutcome.EXPECTED,
        )
        self.assertEqual(result.next_load_factor, 1.0)

    def test_reports_missing_observations(
        self,
    ) -> None:
        result = self.engine.analyze(
            self.workout,
            [],
            pre_session_recovery_score=69,
        )

        self.assertEqual(
            result.outcome,
            TrainingResponseOutcome.INSUFFICIENT,
        )
        self.assertEqual(result.confidence_score, 0)
        self.assertFalse(result.usable_for_learning)


if __name__ == "__main__":
    unittest.main()