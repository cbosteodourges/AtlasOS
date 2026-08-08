"""
Tests des modèles détaillés de séances Atlas Coach.
"""

import unittest
from datetime import date

from src.training.session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    IntensityTarget,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class TrainingSessionModelsTests(unittest.TestCase):
    """Vérifie la représentation des séances complexes."""

    def test_builds_detailed_threshold_session(
        self,
    ) -> None:
        workout = AdaptiveWorkout(
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
                    "tendon.achilles.left",
                    "tendon.achilles.right",
                ],
            ),
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
                WorkoutType.CYCLING,
            ],
        )

        workout.validate()

        self.assertEqual(
            workout.estimated_duration_minutes,
            60,
        )
        self.assertEqual(
            workout.blocks[1].estimated_duration_minutes,
            30.0,
        )
        self.assertEqual(
            workout.expected_response.recovery_max_hours,
            48,
        )

        serialized = workout.to_dict()

        self.assertEqual(
            serialized["workout_type"],
            "threshold_sv2",
        )
        self.assertEqual(serialized["priority"], "key")
        self.assertEqual(
            serialized["blocks"][1]["block_type"],
            "work",
        )

    def test_rejects_active_session_without_blocks(
        self,
    ) -> None:
        workout = AdaptiveWorkout(
            workout_id="invalid",
            workout_date=date(2026, 8, 8),
            workout_type=WorkoutType.ENDURANCE_Z2,
            title="Séance incomplète",
            objective="Test.",
            blocks=[],
        )

        with self.assertRaises(ValueError):
            workout.validate()

    def test_rejects_invalid_expected_load(
        self,
    ) -> None:
        response = ExpectedTrainingResponse(
            physiological_load_0_100=110,
            biomechanical_load_0_100=40,
            recovery_min_hours=24,
            recovery_max_hours=48,
        )

        with self.assertRaises(ValueError):
            response.validate()


if __name__ == "__main__":
    unittest.main()