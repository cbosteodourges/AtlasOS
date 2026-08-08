"""
Test de bout en bout de la boucle adaptative Atlas Coach.
"""

import unittest
from datetime import date

from src.performance.athlete_profile import AthleteProfile
from src.physiology import PhysiologyInput
from src.training.adaptive_loop import AdaptiveTrainingLoop
from src.training.decision_engine import (
    TrainingDecisionAction,
)
from src.training.response_learning import (
    TrainingResponseObservation,
    TrainingResponseOutcome,
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


class AdaptiveTrainingLoopTests(unittest.TestCase):
    """Vérifie la boucle avant et après une séance."""

    def test_runs_complete_adaptive_learning_loop(
        self,
    ) -> None:
        loop = AdaptiveTrainingLoop()

        physiology_input = PhysiologyInput(
            hrv_ms=44.0,
            hrv_baseline_ms=48.0,
            resting_hr_bpm=46.0,
            resting_hr_baseline_bpm=47.5,
            sleep_hours=8.8,
            sleep_need_hours=8.0,
            sleep_quality_0_100=77,
            stress_0_10=2.01,
        )

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
                    "tendon.achilles.right",
                ],
            ),
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
            ],
        )

        preparation = loop.prepare_session(
            physiology_input,
            workout,
        )

        self.assertEqual(
            preparation.physiology.recovery_score,
            68.8,
        )
        self.assertEqual(
            preparation.atlas_index.score,
            69,
        )
        self.assertEqual(
            preparation.decision.action,
            TrainingDecisionAction.REDUCE,
        )
        self.assertEqual(
            preparation.adaptation
            .adapted_workout.blocks[1].repetitions,
            2,
        )

        observations = [
            TrainingResponseObservation(
                workout_id=workout.workout_id,
                hours_after_session=24,
                recovery_score=66,
                atlas_index_score=67,
                fatigue_0_10=4,
                muscle_soreness_0_10=3,
                pain_0_10=2,
                actual_rpe_0_10=6,
            ),
            TrainingResponseObservation(
                workout_id=workout.workout_id,
                hours_after_session=48,
                recovery_score=72,
                atlas_index_score=73,
                fatigue_0_10=2,
                muscle_soreness_0_10=2,
                pain_0_10=1,
                actual_rpe_0_10=6,
            ),
        ]

        learning = loop.learn_from_response(
            preparation,
            observations,
            pre_session_pain_0_10=2,
        )

        self.assertEqual(
            learning.outcome,
            TrainingResponseOutcome.POSITIVE,
        )
        self.assertEqual(
            learning.next_load_factor,
            1.05,
        )
        self.assertTrue(
            learning.usable_for_learning
        )

        profile = AthleteProfile(
            athlete_id="christophe",
            declared_level="competitive",
            observed_level="competitive",
        )
        completed_learning = (
            loop.learn_and_update_profile(
                preparation,
                observations,
                profile,
                pre_session_pain_0_10=2,
            )
        )

        self.assertTrue(
            completed_learning.profile_update.applied
        )
        self.assertEqual(
            profile.tolerance
            .learned_response_count,
            0,
        )
        self.assertEqual(
            completed_learning.profile_update
            .updated_profile.tolerance
            .learned_response_count,
            1,
        )
        self.assertGreater(
            completed_learning.profile_update
            .updated_profile.tolerance
            .learned_physiological_tolerance_score,
            50,
        )


if __name__ == "__main__":
    unittest.main()