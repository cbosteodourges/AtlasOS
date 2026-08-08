"""Tests de conversion Atlas Research vers Atlas Coach."""

import unittest
from datetime import date

from src.performance.athlete_profile import (
    AthleteProfile,
    PhysiologicalReferences,
    TrainingTolerance,
)
from src.research.training_protocol_catalog import (
    build_default_training_protocol_registry,
)
from src.research.training_protocol_selector import (
    TrainingProtocolSelector,
)
from src.training.research_workout_builder import (
    ResearchWorkoutBuilder,
)
from src.training.session_models import (
    WorkoutPriority,
    WorkoutType,
)


def build_profile(
    *,
    with_speeds: bool = True,
) -> AthleteProfile:
    """Construit un profil sportif exploitable."""
    physiological = PhysiologicalReferences()

    if with_speeds:
        physiological.vma_kmh = 14.0
        physiological.threshold_speed_kmh = 12.5

    return AthleteProfile(
        athlete_id="athlete-test",
        declared_level="competitive",
        observed_level="competitive",
        physiological=physiological,
        tolerance=TrainingTolerance(
            learned_physiological_tolerance_score=75,
            learned_biomechanical_tolerance_score=75,
            learned_response_count=10,
        ),
        history_activity_count=200,
        data_quality_score=90,
        profile_confidence_score=90,
    )


def select_protocol(
    workout_type_key: str,
    profile: AthleteProfile,
):
    """Sélectionne un protocole réel du catalogue."""
    selector = TrainingProtocolSelector(
        build_default_training_protocol_registry()
    )
    selections = selector.select(
        profile=profile,
        phase="development",
        goal_distance_km=10.0,
        available_dynamic_metrics={"recovery_status"},
    )

    return next(
        selection
        for selection in selections
        if selection.protocol.workout_type_key
        == workout_type_key
    )


class ResearchWorkoutBuilderTests(unittest.TestCase):
    """Validation de la séance Coach produite."""

    def setUp(self) -> None:
        self.builder = ResearchWorkoutBuilder()
        self.workout_date = date(2026, 8, 10)

    def test_builds_valid_mixed_workout(self) -> None:
        profile = build_profile()
        selection = select_protocol(
            "mixed_threshold_vo2",
            profile,
        )

        workout = self.builder.build(
            selection=selection,
            profile=profile,
            workout_date=self.workout_date,
        )

        self.assertEqual(
            workout.workout_type,
            WorkoutType.MIXED_THRESHOLD_VO2,
        )
        self.assertEqual(
            workout.priority,
            WorkoutPriority.KEY,
        )
        self.assertEqual(len(workout.blocks), 4)
        self.assertEqual(
            workout.estimated_duration_minutes,
            61,
        )
        workout.validate()

    def test_converts_threshold_and_vma_to_speeds(
        self,
    ) -> None:
        profile = build_profile()
        selection = select_protocol(
            "mixed_threshold_vo2",
            profile,
        )

        workout = self.builder.build(
            selection=selection,
            profile=profile,
            workout_date=self.workout_date,
        )
        threshold_block = workout.blocks[1]
        vo2_block = workout.blocks[2]

        self.assertEqual(
            threshold_block.target.speed_min_kmh,
            11.88,
        )
        self.assertEqual(
            threshold_block.target.speed_max_kmh,
            12.5,
        )
        self.assertEqual(
            vo2_block.target.speed_min_kmh,
            13.3,
        )
        self.assertEqual(
            vo2_block.target.speed_max_kmh,
            14.0,
        )

    def test_preserves_hill_gradient_and_biomechanical_load(
        self,
    ) -> None:
        profile = build_profile()
        selection = select_protocol(
            "hill_sprints",
            profile,
        )

        workout = self.builder.build(
            selection=selection,
            profile=profile,
            workout_date=self.workout_date,
        )
        work_block = workout.blocks[1]

        self.assertEqual(
            work_block.target.gradient_min_percent,
            6,
        )
        self.assertEqual(
            work_block.target.gradient_max_percent,
            10,
        )
        self.assertEqual(
            work_block.target.rpe_0_10,
            9.5,
        )
        self.assertEqual(
            workout.expected_response.biomechanical_load_0_100,
            85,
        )

    def test_preserves_triangular_intensity_pattern(
        self,
    ) -> None:
        profile = build_profile()
        selection = select_protocol(
            "triangular_vo2",
            profile,
        )

        workout = self.builder.build(
            selection=selection,
            profile=profile,
            workout_date=self.workout_date,
        )

        self.assertEqual(
            workout.blocks[1].target.intensity_pattern,
            "triangular",
        )

    def test_remains_valid_when_speed_metric_is_missing(
        self,
    ) -> None:
        profile = build_profile(with_speeds=False)
        selection = select_protocol(
            "triangular_vo2",
            profile,
        )

        workout = self.builder.build(
            selection=selection,
            profile=profile,
            workout_date=self.workout_date,
        )

        self.assertIsNone(
            workout.blocks[1].target.speed_min_kmh
        )
        self.assertEqual(
            workout.blocks[1].target.rpe_0_10,
            9.0,
        )
        self.assertTrue(workout.coach_notes)
        workout.validate()

    def test_workout_is_serializable(self) -> None:
        profile = build_profile()
        selection = select_protocol(
            "hill_sprints",
            profile,
        )

        workout = self.builder.build(
            selection=selection,
            profile=profile,
            workout_date=self.workout_date,
        )
        result = workout.to_dict()

        self.assertEqual(
            result["workout_type"],
            "hill_sprints",
        )
        self.assertEqual(
            result["workout_date"],
            "2026-08-10",
        )


if __name__ == "__main__":
    unittest.main()