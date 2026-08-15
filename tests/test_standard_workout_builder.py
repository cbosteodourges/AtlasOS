"""Tests des séances fondamentales Atlas Coach."""

import unittest
from datetime import date

from src.performance.athlete_profile import (
    AthleteProfile,
    PhysiologicalReferences,
)
from src.performance.models import PerformanceGoal
from src.training.session_models import (
    BlockType,
    WorkoutType,
)
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

    def test_builds_historical_interval_variants(
        self,
    ) -> None:
        short = self.builder.build_short_intervals(
            profile=build_profile(),
            workout_date=self.workout_date,
            repetitions=8,
            distance_meters=400,
        )
        threshold = self.builder.build_threshold_intervals(
            profile=build_profile(),
            workout_date=self.workout_date,
            repetitions=5,
            distance_meters=1000,
        )
        mixed = self.builder.build_mixed_intervals(
            profile=build_profile(),
            workout_date=self.workout_date,
            repetitions=4,
            threshold_distance_meters=1000,
            vo2_distance_meters=400,
        )

        self.assertEqual(
            short.workout_type,
            WorkoutType.VMA_SHORT,
        )
        self.assertEqual(short.blocks[1].repetitions, 8)
        self.assertEqual(
            short.blocks[1].distance_meters,
            400,
        )
        self.assertEqual(
            short.blocks[1].target.speed_min_kmh,
            13.3,
        )

        self.assertEqual(
            threshold.workout_type,
            WorkoutType.THRESHOLD_SV2,
        )
        self.assertEqual(
            threshold.blocks[1].repetitions,
            5,
        )
        self.assertEqual(
            threshold.blocks[1].distance_meters,
            1000,
        )

        mixed_work = [
            block
            for block in mixed.blocks
            if block.block_type == BlockType.WORK
        ]
        self.assertEqual(
            mixed.workout_type,
            WorkoutType.MIXED_THRESHOLD_VO2,
        )
        self.assertEqual(len(mixed_work), 8)
        self.assertEqual(
            [
                block.distance_meters
                for block in mixed_work[:4]
            ],
            [1000, 400, 1000, 400],
        )
        short.validate()
        threshold.validate()
        mixed.validate()

    def test_builds_historical_specific_long_run(
        self,
    ) -> None:
        goal = PerformanceGoal(
            name="Semi-marathon de Lille",
            event_date=date(2026, 10, 25),
            distance_km=21.1,
            target_time_minutes=109,
        )

        workout = self.builder.build_specific_long_run(
            profile=build_profile(),
            goal=goal,
            workout_date=self.workout_date,
            group_distances_meters=[
                4000,
                3000,
                3000,
            ],
        )
        work_blocks = [
            block
            for block in workout.blocks
            if block.block_type == BlockType.WORK
        ]

        self.assertEqual(
            workout.workout_type,
            WorkoutType.LONG_RUN,
        )
        self.assertEqual(
            [
                block.distance_meters
                for block in work_blocks
            ],
            [4000, 3000, 3000],
        )
        self.assertTrue(all(
            block.target.speed_min_kmh == 11.61
            for block in work_blocks
        ))
        self.assertEqual(
            workout.planned_distance_km,
            17.0,
        )
        workout.validate()
    def test_builds_half_marathon_race_sharpening(
        self,
    ) -> None:
        goal = PerformanceGoal(
            name="Semi-marathon de Lille",
            event_date=date(2026, 10, 25),
            distance_km=21.1,
            target_time_minutes=109,
        )

        workout = self.builder.build_race_sharpening(
            profile=build_profile(),
            goal=goal,
            workout_date=date(2026, 10, 20),
        )
        work_block = workout.blocks[1]
        target = work_block.target

        self.assertEqual(
            workout.workout_type,
            WorkoutType.TEMPO_Z3,
        )
        self.assertEqual(
            workout.workout_date,
            date(2026, 10, 20),
        )
        self.assertEqual(work_block.repetitions, 3)
        self.assertEqual(work_block.duration_minutes, 5)
        self.assertEqual(work_block.recovery_minutes, 2)
        self.assertEqual(target.speed_min_kmh, 11.61)
        self.assertEqual(target.pace_min_per_km, "5:10")
        self.assertEqual(target.heart_rate_min_bpm, 144)
        self.assertEqual(target.heart_rate_max_bpm, 154)
        self.assertEqual(
            workout.expected_response.recovery_max_hours,
            36,
        )
        self.assertTrue(workout.movable)
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