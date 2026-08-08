"""
Tests du moteur d’adaptation des séances Atlas Coach.
"""

import unittest
from datetime import date

from src.training.adaptation_engine import (
    WorkoutAdaptationEngine,
)
from src.training.decision_engine import (
    TrainingDecision,
    TrainingDecisionAction,
)
from src.training.session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    IntensityTarget,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class WorkoutAdaptationEngineTests(unittest.TestCase):
    """Vérifie les transformations concrètes des séances."""

    def setUp(self) -> None:
        self.engine = WorkoutAdaptationEngine()

    @staticmethod
    def threshold_workout() -> AdaptiveWorkout:
        return AdaptiveWorkout(
            workout_id="threshold-2026-08-08",
            workout_date=date(2026, 8, 8),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="3 × 8 minutes au SV2",
            objective="Développer l’allure au seuil.",
            priority=WorkoutPriority.KEY,
            blocks=[
                TrainingBlock(
                    name="Échauffement",
                    block_type=BlockType.WARM_UP,
                    duration_minutes=20,
                    target=IntensityTarget(
                        zone=2,
                        rpe_0_10=3,
                    ),
                ),
                TrainingBlock(
                    name="Travail au seuil",
                    block_type=BlockType.WORK,
                    repetitions=3,
                    duration_minutes=8,
                    recovery_minutes=3,
                    target=IntensityTarget(
                        zone=4,
                        speed_min_kmh=12.7,
                        speed_max_kmh=13.1,
                        rpe_0_10=7,
                    ),
                ),
                TrainingBlock(
                    name="Retour au calme",
                    block_type=BlockType.COOL_DOWN,
                    duration_minutes=10,
                    target=IntensityTarget(
                        zone=1,
                        rpe_0_10=2,
                    ),
                ),
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
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
            ],
        )

    @staticmethod
    def decision(
        action: TrainingDecisionAction,
        *,
        duration_factor: float = 1.0,
        intensity_factor: float = 1.0,
        replacement_type: WorkoutType | None = None,
        shift_days: int = 0,
    ) -> TrainingDecision:
        return TrainingDecision(
            workout_id="threshold-2026-08-08",
            action=action,
            atlas_index_score=69,
            session_demand_score=66,
            compatibility_score=63,
            duration_factor=duration_factor,
            intensity_factor=intensity_factor,
            replacement_type=replacement_type,
            shift_days=shift_days,
            reasons=["Test."],
        )

    def test_reduces_work_without_mutating_original(
        self,
    ) -> None:
        workout = self.threshold_workout()

        result = self.engine.adapt(
            workout,
            self.decision(
                TrainingDecisionAction.REDUCE,
                duration_factor=0.85,
                intensity_factor=0.90,
            ),
        )

        work_block = result.adapted_workout.blocks[1]

        self.assertEqual(workout.blocks[1].repetitions, 3)
        self.assertEqual(workout.blocks[1].target.rpe_0_10, 7)
        self.assertEqual(work_block.repetitions, 2)
        self.assertEqual(work_block.duration_minutes, 8)
        self.assertEqual(work_block.target.rpe_0_10, 6.3)
        self.assertEqual(
            result.adapted_workout.expected_response
            .physiological_load_0_100,
            55,
        )
        self.assertTrue(result.modifications)

    def test_replaces_with_structured_easy_session(
        self,
    ) -> None:
        workout = self.threshold_workout()

        result = self.engine.adapt(
            workout,
            self.decision(
                TrainingDecisionAction.REPLACE,
                duration_factor=0.70,
                intensity_factor=0.75,
                replacement_type=WorkoutType.ENDURANCE_Z2,
            ),
        )

        adapted = result.adapted_workout

        self.assertEqual(
            adapted.workout_type,
            WorkoutType.ENDURANCE_Z2,
        )
        self.assertEqual(
            adapted.title,
            "Endurance facile de substitution",
        )
        self.assertEqual(adapted.estimated_duration_minutes, 42)
        self.assertEqual(len(adapted.blocks), 3)
        self.assertEqual(
            adapted.expected_response
            .physiological_load_0_100,
            35,
        )

    def test_postpones_without_changing_content(
        self,
    ) -> None:
        workout = self.threshold_workout()

        result = self.engine.adapt(
            workout,
            self.decision(
                TrainingDecisionAction.POSTPONE,
                shift_days=1,
            ),
        )

        self.assertEqual(
            workout.workout_date,
            date(2026, 8, 8),
        )
        self.assertEqual(
            result.adapted_workout.workout_date,
            date(2026, 8, 9),
        )
        self.assertEqual(
            result.adapted_workout.blocks[1].repetitions,
            3,
        )

    def test_cancels_as_explicit_rest_day(
        self,
    ) -> None:
        result = self.engine.adapt(
            self.threshold_workout(),
            self.decision(
                TrainingDecisionAction.CANCEL,
                duration_factor=0.0,
                intensity_factor=0.0,
                replacement_type=WorkoutType.REST,
            ),
        )

        adapted = result.adapted_workout

        self.assertEqual(
            adapted.workout_type,
            WorkoutType.REST,
        )
        self.assertEqual(adapted.blocks, [])
        self.assertEqual(adapted.estimated_duration_minutes, 0)
        self.assertEqual(
            adapted.expected_response
            .physiological_load_0_100,
            0,
        )


if __name__ == "__main__":
    unittest.main()