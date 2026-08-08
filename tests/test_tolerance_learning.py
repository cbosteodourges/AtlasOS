"""
Tests de la mémoire adaptative du profil athlète.
"""

import unittest
from datetime import date, datetime, timezone

from src.performance.athlete_profile import AthleteProfile
from src.training.response_learning import (
    TrainingResponseLearning,
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
from src.training.tolerance_learning import (
    AthleteToleranceLearningEngine,
)


class AthleteToleranceLearningEngineTests(unittest.TestCase):
    """Vérifie l’application durable des réponses fiables."""

    def setUp(self) -> None:
        self.engine = AthleteToleranceLearningEngine()
        self.profile = AthleteProfile(
            athlete_id="christophe",
            declared_level="competitive",
            observed_level="competitive",
        )
        self.workout = AdaptiveWorkout(
            workout_id="threshold-2026-08-08",
            workout_date=date(2026, 8, 8),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="Séance au seuil",
            objective="Développer le SV2.",
            priority=WorkoutPriority.KEY,
            blocks=[
                TrainingBlock(
                    name="Travail au seuil",
                    block_type=BlockType.WORK,
                    duration_minutes=30,
                )
            ],
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=72,
                biomechanical_load_0_100=58,
                recovery_min_hours=36,
                recovery_max_hours=48,
                sensitive_structures=[
                    "tendon.achilles.right",
                ],
            ),
        )

    @staticmethod
    def learning(
        outcome: TrainingResponseOutcome,
        *,
        confidence: int,
        physiological_delta: int,
        biomechanical_delta: int,
        usable: bool = True,
    ) -> TrainingResponseLearning:
        return TrainingResponseLearning(
            workout_id="threshold-2026-08-08",
            outcome=outcome,
            confidence_score=confidence,
            next_load_factor=1.0,
            physiological_tolerance_delta=(
                physiological_delta
            ),
            biomechanical_tolerance_delta=(
                biomechanical_delta
            ),
            usable_for_learning=usable,
            observations_count=2,
            latest_checkpoint_hours=48,
            reasons=[],
            alerts=[],
        )

    def test_positive_response_increases_tolerance(
        self,
    ) -> None:
        result = self.engine.apply(
            self.profile,
            self.workout,
            self.learning(
                TrainingResponseOutcome.POSITIVE,
                confidence=80,
                physiological_delta=2,
                biomechanical_delta=2,
            ),
            learned_at=datetime(
                2026, 8, 10,
                tzinfo=timezone.utc,
            ),
        )
        tolerance = result.updated_profile.tolerance

        self.assertTrue(result.applied)
        self.assertEqual(
            self.profile.tolerance
            .learned_physiological_tolerance_score,
            50.0,
        )
        self.assertEqual(
            tolerance
            .learned_physiological_tolerance_score,
            51.6,
        )
        self.assertEqual(
            tolerance
            .learned_biomechanical_tolerance_score,
            51.6,
        )
        self.assertEqual(
            tolerance.session_type_tolerance_scores[
                "threshold_sv2"
            ],
            51.6,
        )
        self.assertEqual(
            tolerance.structure_tolerance_scores[
                "tendon.achilles.right"
            ],
            51.6,
        )
        self.assertEqual(
            tolerance.learned_response_count,
            1,
        )
        self.assertEqual(
            tolerance.positive_response_count,
            1,
        )

    def test_delayed_response_reduces_tolerance(
        self,
    ) -> None:
        result = self.engine.apply(
            self.profile,
            self.workout,
            self.learning(
                TrainingResponseOutcome.DELAYED,
                confidence=80,
                physiological_delta=-5,
                biomechanical_delta=-4,
            ),
        )
        tolerance = result.updated_profile.tolerance

        self.assertEqual(
            tolerance
            .learned_physiological_tolerance_score,
            46.0,
        )
        self.assertEqual(
            tolerance
            .learned_biomechanical_tolerance_score,
            46.8,
        )
        self.assertEqual(
            tolerance.delayed_response_count,
            1,
        )

    def test_ignores_low_confidence_response(
        self,
    ) -> None:
        result = self.engine.apply(
            self.profile,
            self.workout,
            self.learning(
                TrainingResponseOutcome.INSUFFICIENT,
                confidence=40,
                physiological_delta=0,
                biomechanical_delta=0,
                usable=False,
            ),
        )

        self.assertFalse(result.applied)
        self.assertEqual(
            result.updated_profile.tolerance
            .learned_response_count,
            0,
        )
        self.assertEqual(
            result.updated_profile.tolerance
            .session_type_tolerance_scores,
            {},
        )


if __name__ == "__main__":
    unittest.main()