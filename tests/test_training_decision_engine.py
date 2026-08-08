"""
Tests du moteur de décision quotidienne Atlas Coach.
"""

import unittest
from datetime import date

from src.atlas_brain.atlas_index import AtlasIndexResult
from src.training.decision_engine import (
    TrainingDecisionAction,
    TrainingDecisionEngine,
)
from src.training.session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class TrainingDecisionEngineTests(unittest.TestCase):
    """Vérifie les décisions selon capacité et séance."""

    def setUp(self) -> None:
        self.engine = TrainingDecisionEngine()

    @staticmethod
    def atlas_index(
        score: int,
        *,
        readiness: int | None = None,
        tolerance: int | None = 80,
        alerts: list[str] | None = None,
    ) -> AtlasIndexResult:
        return AtlasIndexResult(
            score=score,
            status="TEST",
            recovery_score=score,
            training_readiness_score=(
                score if readiness is None else readiness
            ),
            biomechanical_tolerance_score=tolerance,
            data_confidence_score=85,
            alerts=alerts or [],
            explanations=[],
        )

    @staticmethod
    def workout(
        workout_type: WorkoutType,
        *,
        priority: WorkoutPriority = WorkoutPriority.SUPPORT,
        physiological_load: int = 45,
        biomechanical_load: int = 40,
        movable: bool = True,
    ) -> AdaptiveWorkout:
        return AdaptiveWorkout(
            workout_id=f"test-{workout_type.value}",
            workout_date=date(2026, 8, 8),
            workout_type=workout_type,
            title="Séance test",
            objective="Tester la décision.",
            priority=priority,
            blocks=[
                TrainingBlock(
                    name="Bloc principal",
                    block_type=BlockType.CONTINUOUS,
                    duration_minutes=40,
                )
            ],
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=physiological_load,
                biomechanical_load_0_100=biomechanical_load,
                recovery_min_hours=24,
                recovery_max_hours=48,
            ),
            movable=movable,
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
            ],
        )

    def test_maintains_compatible_easy_session(
        self,
    ) -> None:
        decision = self.engine.decide(
            self.atlas_index(82),
            self.workout(WorkoutType.ENDURANCE_Z2),
        )

        self.assertEqual(
            decision.action,
            TrainingDecisionAction.MAINTAIN,
        )
        self.assertEqual(decision.duration_factor, 1.0)
        self.assertEqual(decision.intensity_factor, 1.0)

    def test_reduces_intense_session_when_available(
        self,
    ) -> None:
        decision = self.engine.decide(
            self.atlas_index(69),
            self.workout(
                WorkoutType.THRESHOLD_SV2,
                priority=WorkoutPriority.KEY,
                physiological_load=72,
                biomechanical_load=58,
            ),
        )

        self.assertEqual(
            decision.action,
            TrainingDecisionAction.REDUCE,
        )
        self.assertEqual(decision.duration_factor, 0.85)
        self.assertEqual(decision.intensity_factor, 0.90)

    def test_replaces_intense_session_when_limited(
        self,
    ) -> None:
        decision = self.engine.decide(
            self.atlas_index(60),
            self.workout(
                WorkoutType.VMA_SHORT,
                physiological_load=78,
                biomechanical_load=72,
            ),
        )

        self.assertEqual(
            decision.action,
            TrainingDecisionAction.REPLACE,
        )
        self.assertEqual(
            decision.replacement_type,
            WorkoutType.ENDURANCE_Z2,
        )

    def test_postpones_key_session_when_possible(
        self,
    ) -> None:
        decision = self.engine.decide(
            self.atlas_index(45),
            self.workout(
                WorkoutType.RACE_SPECIFIC,
                priority=WorkoutPriority.KEY,
                physiological_load=80,
                biomechanical_load=65,
                movable=True,
            ),
        )

        self.assertEqual(
            decision.action,
            TrainingDecisionAction.POSTPONE,
        )
        self.assertEqual(decision.shift_days, 1)

    def test_cancels_session_on_safety_alert(
        self,
    ) -> None:
        decision = self.engine.decide(
            self.atlas_index(
                30,
                alerts=["Symptômes de maladie signalés."],
            ),
            self.workout(WorkoutType.ENDURANCE_Z2),
        )

        self.assertEqual(
            decision.action,
            TrainingDecisionAction.CANCEL,
        )
        self.assertEqual(
            decision.replacement_type,
            WorkoutType.REST,
        )
        self.assertEqual(decision.duration_factor, 0.0)
        self.assertEqual(
            decision.safety_alerts,
            ["Symptômes de maladie signalés."],
        )


if __name__ == "__main__":
    unittest.main()