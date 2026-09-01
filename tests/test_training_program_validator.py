"""Tests du contrôle universel avant publication d'un programme."""

from copy import deepcopy
from datetime import date
import unittest

from src.performance.models import PerformanceGoal
from src.training.program_generator import TrainingProgramGenerator
from src.training.program_validator import TrainingProgramValidator
from src.training.session_models import BlockType
from test_training_program_generator import build_profile, build_settings


class TrainingProgramValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = TrainingProgramValidator()
        self.start_date = date(2026, 6, 1)
        self.event_date = date(2026, 8, 23)

    def _generate(self, distance_km: float, name: str):
        target_minutes = max(20, round(distance_km * 5))
        return TrainingProgramGenerator().generate(
            profile=build_profile(),
            goal=PerformanceGoal(
                name=name,
                event_date=self.event_date,
                distance_km=distance_km,
                target_time_minutes=target_minutes,
            ),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )

    def test_validates_distance_matrix(self) -> None:
        cases = (
            (5.0, "5 km route"),
            (10.0, "10 km route"),
            (21.1, "Semi-marathon"),
            (30.0, "Trail 30 km"),
            (42.195, "Marathon"),
        )
        for distance_km, name in cases:
            with self.subTest(distance_km=distance_km):
                program = self._generate(distance_km, name)
                report = self.validator.validate(
                    program,
                    profile=build_profile(),
                )
                self.assertTrue(
                    report.valid,
                    [issue.format() for issue in report.errors],
                )
                races = [
                    workout
                    for week in program.weeks
                    for workout in week.workouts
                    if workout.workout_type.value == "race_specific"
                ]
                self.assertEqual(len(races), 1)
                self.assertAlmostEqual(
                    races[0].planned_distance_km,
                    distance_km,
                    places=3,
                )

    def test_accepts_partial_physiological_data(self) -> None:
        program = TrainingProgramGenerator().generate(
            profile=build_profile(with_metrics=False),
            goal=PerformanceGoal(
                name="10 km sans métriques complètes",
                event_date=self.event_date,
                distance_km=10.0,
                target_time_minutes=None,
            ),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )
        report = self.validator.validate(
            program,
            profile=build_profile(with_metrics=False),
        )
        self.assertTrue(report.valid)
        self.assertTrue(
            any("Mesures manquantes" in item for item in program.warnings)
        )

    def test_rejects_duplicate_workout_identifier(self) -> None:
        program = self._generate(10.0, "10 km")
        workouts = [
            workout
            for week in program.weeks
            for workout in week.workouts
        ]
        workouts[1].workout_id = workouts[0].workout_id

        report = self.validator.validate(program)
        self.assertFalse(report.valid)
        self.assertIn(
            "DUPLICATE_WORKOUT_ID",
            {issue.code for issue in report.errors},
        )

    def test_rejects_inverted_target_range(self) -> None:
        program = self._generate(10.0, "10 km")
        block = next(
            block
            for week in program.weeks
            for workout in week.workouts
            for block in workout.blocks
            if block.target.speed_min_kmh is not None
            and block.target.speed_max_kmh is not None
        )
        block.target.speed_min_kmh = block.target.speed_max_kmh + 1

        report = self.validator.validate(program)
        self.assertIn(
            "TARGET_RANGE",
            {issue.code for issue in report.errors},
        )

    def test_rejects_title_only_interval_structure(self) -> None:
        program = self._generate(10.0, "10 km")
        workout = next(
            workout
            for week in program.weeks
            for workout in week.workouts
            if any(
                block.block_type == BlockType.WORK
                for block in workout.blocks
            )
        )
        workout.title = "6 × 1000 m"
        for block in workout.blocks:
            if block.block_type == BlockType.WORK:
                block.block_type = BlockType.CONTINUOUS

        report = self.validator.validate(program)
        self.assertIn(
            "TITLE_WITHOUT_STRUCTURE",
            {issue.code for issue in report.errors},
        )

    def test_rejects_invalid_goal_before_building(self) -> None:
        with self.assertRaisesRegex(ValueError, "distance.*positive"):
            self._generate(0.0, "Distance invalide")

        with self.assertRaisesRegex(ValueError, "date de début"):
            TrainingProgramGenerator().generate(
                profile=build_profile(),
                goal=PerformanceGoal(
                    name="Objectif passé",
                    event_date=date(2026, 5, 31),
                    distance_km=10.0,
                ),
                start_date=self.start_date,
                settings=build_settings(),
            )

    def test_raise_for_errors_stops_publication(self) -> None:
        program = deepcopy(self._generate(10.0, "10 km"))
        program.end_date = program.start_date
        report = self.validator.validate(program)

        with self.assertRaisesRegex(
            ValueError,
            "Programme refusé avant publication",
        ):
            report.raise_for_errors()


if __name__ == "__main__":
    unittest.main()
