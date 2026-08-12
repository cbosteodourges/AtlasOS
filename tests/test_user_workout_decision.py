import unittest

from src.training.decision_engine import TrainingDecisionAction
from src.training.training_program_loader import TrainingProgramLoader
from src.training.user_workout_decision import (
    UserWorkoutDecisionEngine,
    UserWorkoutStatus,
)


class UserWorkoutDecisionEngineTests(unittest.TestCase):
    def workout(self, priority="support"):
        payload = {
            "weeks": [
                {
                    "workouts": [
                        {
                            "workout_id": "2026-08-12-cycling",
                            "workout_date": "2026-08-12",
                            "workout_type": "cycling",
                            "title": "Vélo endurance croisée",
                            "objective": "Entretenir le volume aérobie.",
                            "sport": "cycling",
                            "priority": priority,
                            "planned_duration_minutes": 60,
                            "movable": True,
                            "maximum_shift_days": 2,
                            "expected_response": {
                                "physiological_load_0_100": 40,
                                "biomechanical_load_0_100": 20,
                                "recovery_min_hours": 12,
                                "recovery_max_hours": 24,
                                "sensitive_structures": [],
                            },
                            "blocks": [
                                {
                                    "name": "Endurance continue",
                                    "block_type": "continuous",
                                    "repetitions": 1,
                                    "duration_minutes": 60,
                                    "target": {
                                        "zone": 2,
                                        "rpe_0_10": 3.5,
                                        "intensity_pattern": "constant",
                                    },
                                }
                            ],
                        }
                    ]
                }
            ]
        }
        return TrainingProgramLoader().from_payload(payload)[0]

    def test_skipped_support_workout_is_not_postponed(self):
        result = UserWorkoutDecisionEngine().skip(
            self.workout("support"),
            reason="Choix personnel",
            sessions_on_next_day=2,
        )

        self.assertEqual(result.status, UserWorkoutStatus.SKIPPED)
        self.assertEqual(
            result.action,
            TrainingDecisionAction.CANCEL,
        )
        self.assertFalse(result.recalculate_future_program)
        self.assertEqual(result.removed_duration_minutes, 60)
        self.assertEqual(result.removed_physiological_load, 40)
        self.assertEqual(result.removed_biomechanical_load, 20)
        self.assertEqual(result.shift_days, 0)

    def test_skipped_key_workout_requests_recalculation(self):
        result = UserWorkoutDecisionEngine().skip(
            self.workout("key"),
            reason="Indisponibilité",
            sessions_on_next_day=0,
        )

        self.assertEqual(
            result.action,
            TrainingDecisionAction.POSTPONE,
        )
        self.assertTrue(result.recalculate_future_program)
        self.assertEqual(result.shift_days, 1)


if __name__ == "__main__":
    unittest.main()