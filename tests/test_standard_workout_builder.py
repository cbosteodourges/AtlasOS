"""Tests des séances fondamentales Atlas Coach."""

import unittest
from datetime import date

from src.performance.athlete_profile import (
    AthleteProfile,
    PhysiologicalReferences,
)
from src.performance.models import PerformanceGoal
from src.training.session_models import WorkoutType
from src.training.standard_workout_builder import (
    StandardWorkoutBuilder,
)


def build_profile(
    vma_kmh: float | None = 14.0,
) -> AthleteProfile:
    """Construit un profil minimal pour les tests."""
    return AthleteProfile(
        athlete_id="athlete-test",
        declared_level="competitive",
        observed_level="competitive",
        physiological=PhysiologicalReferences(
            vma_kmh=vma_kmh,
            threshold_heart_rate_bpm=160,
        ),
    )


class StandardWorkoutBuilderTests(unittest.TestCase):
    """Validation des séances non issues du registre."""

    def setUp(self) -> None:
        self.builder = StandardWorkoutBuilder()
        self.workout_date = date(2026, 8, 10)

    def test_builds_personalized_endurance_z2(self) -> None:
        workout = self.builder.build_endurance(
            profile=build_profile(),
            workout_date=self.workout_date,
            duration_minutes=50,
        )

        self.assertEqual(
            workout.workout_type,
            WorkoutType.ENDURANCE_Z2,
        )
        self.assertEqual(
            workout.blocks[0].target.speed_min_kmh,
            9.52,
        )
        self.assertEqual(
            workout.blocks[0].target.speed_max_kmh,
            10.08,
        )
        self.assertEqual(
            workout.blocks[0].target.heart_rate_min_bpm,
            120,
        )
        self.assertEqual(
            workout.blocks[0].target.heart_rate_max_bpm,
            138,
        )
        self.assertEqual(
            workout.estimated_duration_minutes,
            50,
        )
        workout.validate()

    def test_builds_lighter_recovery_run(self) -> None:
        workout = self.builder.build_endurance(
            profile=build_profile(),
            workout_date=self.workout_date,
            duration_minutes=35,
            recovery=True,
        )

        self.assertEqual(
            workout.workout_type,
            WorkoutType.RECOVERY_RUN,
        )
        self.assertEqual(
            workout.expected_response.physiological_load_0_100,
            25,
        )

    def test_builds_long_run_with_expected_recovery(
        self,
    ) -> None:
        workout = self.builder.build_long_run(
            profile=build_profile(),
            workout_date=self.workout_date,
            duration_minutes=90,
        )

        self.assertEqual(
            workout.workout_type,
            WorkoutType.LONG_RUN,
        )
        self.assertEqual(
            workout.expected_response.recovery_min_hours,
            36,
        )
        self.assertEqual(
            workout.estimated_duration_minutes,
            90,
        )

    def test_builds_strength_and_mobility_sessions(
        self,
    ) -> None:
        strength = self.builder.build_strength(
            workout_date=self.workout_date,
        )
        mobility = self.builder.build_mobility(
            workout_date=self.workout_date,
        )

        self.assertEqual(strength.sport, "strength")
        self.assertEqual(mobility.sport, "mobility")
        self.assertEqual(
            strength.workout_type,
            WorkoutType.STRENGTH,
        )
        self.assertEqual(
            mobility.workout_type,
            WorkoutType.MOBILITY,
        )
        strength.validate()
        mobility.validate()

    def test_builds_race_from_goal(self) -> None:
        goal = PerformanceGoal(
            name="10 km objectif",
            event_date=date(2026, 9, 20),
            distance_km=10.0,
            target_time_minutes=47,
        )

        workout = self.builder.build_race(goal=goal)
        target = workout.blocks[0].target

        self.assertEqual(
            workout.workout_date,
            goal.event_date,
        )
        self.assertEqual(
            workout.planned_distance_km,
            10.0,
        )
        self.assertEqual(
            target.pace_min_per_km,
            "4:42",
        )
        self.assertEqual(
            target.speed_min_kmh,
            12.77,
        )
        self.assertFalse(workout.movable)
        workout.validate()

    def test_remains_valid_without_vma(self) -> None:
        workout = self.builder.build_endurance(
            profile=build_profile(vma_kmh=None),
            workout_date=self.workout_date,
            duration_minutes=45,
        )

        self.assertIsNone(
            workout.blocks[0].target.speed_min_kmh
        )
        self.assertEqual(
            workout.blocks[0].target.rpe_0_10,
            3.5,
        )
        workout.validate()

    def test_workouts_are_serializable(self) -> None:
        workout = self.builder.build_long_run(
            profile=build_profile(),
            workout_date=self.workout_date,
            duration_minutes=80,
        )

        result = workout.to_dict()

        self.assertEqual(
            result["workout_type"],
            "long_run",
        )
        self.assertEqual(
            result["workout_date"],
            "2026-08-10",
        )


if __name__ == "__main__":
    unittest.main()