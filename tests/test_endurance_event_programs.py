"""Programmes réellement spécialisés marathon et trail."""

from datetime import date
import unittest

from src.performance.models import PerformanceGoal
from src.training.program_generator import TrainingProgramGenerator
from src.training.session_models import WorkoutType
from test_training_program_generator import build_profile, build_settings


class EnduranceEventProgramTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start_date = date(2026, 1, 5)
        self.profile = build_profile()
        self.profile.tolerance.usual_running_distance_per_week_km = 55
        self.profile.tolerance.maximum_tolerated_weekly_distance_km = 70
        self.settings = build_settings(running_sessions=4)
        self.settings.strength_sessions_per_week = 1

    def _generate(
        self,
        *,
        name: str,
        event_date: date,
        distance_km: float,
        target_time_minutes: int,
        discipline: str = "running",
        elevation_gain_m: int | None = None,
        technicality: str = "unknown",
    ):
        return TrainingProgramGenerator().generate(
            profile=self.profile,
            goal=PerformanceGoal(
                name=name,
                event_date=event_date,
                distance_km=distance_km,
                target_time_minutes=target_time_minutes,
                discipline=discipline,
                elevation_gain_m=elevation_gain_m,
                elevation_loss_m=elevation_gain_m,
                terrain_technicality=technicality,
            ),
            start_date=self.start_date,
            settings=self.settings,
            available_dynamic_metrics={"recovery_status"},
        )

    @staticmethod
    def _workouts(program):
        return [
            workout
            for week in program.weeks
            for workout in week.workouts
        ]

    def test_builds_marathon_specific_program(self) -> None:
        program = self._generate(
            name="Marathon route",
            event_date=date(2026, 5, 24),
            distance_km=42.195,
            target_time_minutes=240,
        )
        workouts = self._workouts(program)
        long_runs = [
            item for item in workouts
            if item.workout_type == WorkoutType.LONG_RUN
        ]
        marathon_blocks = [
            item for item in workouts
            if item.title.startswith("Allure marathon")
        ]

        self.assertIn("Spécialisation Marathon route", program.explanation)
        self.assertTrue(marathon_blocks)
        self.assertGreaterEqual(
            max(item.planned_duration_minutes for item in long_runs),
            170,
        )
        self.assertTrue(all(
            item.fueling_strategy for item in long_runs
        ))
        race = next(
            item for item in workouts
            if item.workout_type == WorkoutType.RACE_SPECIFIC
        )
        self.assertEqual(race.planned_distance_km, 42.195)
        self.assertEqual(race.terrain_focus, "route")
        self.assertTrue(race.fueling_strategy)

    def test_builds_each_trail_distance_family(self) -> None:
        cases = (
            (
                20.0,
                "Trail 20 km",
                date(2026, 4, 12),
                800,
                150,
                False,
                "Trail court 20 km",
            ),
            (
                50.0,
                "Trail 50 km",
                date(2026, 5, 31),
                2500,
                420,
                True,
                "Trail long 50 km",
            ),
            (
                70.0,
                "Trail 70 km",
                date(2026, 6, 28),
                4000,
                660,
                True,
                "Ultra-trail 70 km",
            ),
            (
                100.0,
                "Trail 100 km",
                date(2026, 8, 23),
                6000,
                1020,
                True,
                "Ultra-trail 100 km",
            ),
        )
        for (
            distance,
            name,
            event_date,
            elevation,
            target_time,
            expects_back_to_back,
            label,
        ) in cases:
            with self.subTest(distance=distance):
                program = self._generate(
                    name=name,
                    event_date=event_date,
                    distance_km=distance,
                    target_time_minutes=target_time,
                    discipline="trail_running",
                    elevation_gain_m=elevation,
                    technicality="high",
                )
                workouts = self._workouts(program)
                trail_quality = [
                    item for item in workouts
                    if item.title.startswith("Côtes spécifiques")
                ]
                long_runs = [
                    item for item in workouts
                    if item.workout_type == WorkoutType.LONG_RUN
                ]
                race = next(
                    item for item in workouts
                    if item.workout_type == WorkoutType.RACE_SPECIFIC
                )

                self.assertIn(
                    f"Spécialisation {label}",
                    program.explanation,
                )
                self.assertTrue(trail_quality)
                self.assertTrue(long_runs)
                self.assertTrue(all(
                    item.planned_elevation_gain_m
                    and item.planned_elevation_gain_m > 0
                    for item in long_runs
                ))
                self.assertTrue(all(
                    item.fueling_strategy for item in long_runs
                ))
                self.assertEqual(
                    race.planned_elevation_gain_m,
                    elevation,
                )
                self.assertEqual(
                    race.terrain_focus,
                    "trail high",
                )
                chained = [
                    item for item in long_runs
                    if item.title.startswith("Week-end enchaîné")
                ]
                self.assertEqual(bool(chained), expects_back_to_back)

    def test_rejects_trail_without_elevation_or_technicality(self) -> None:
        with self.assertRaisesRegex(ValueError, "dénivelé positif"):
            self._generate(
                name="Trail 50 km",
                event_date=date(2026, 5, 31),
                distance_km=50,
                target_time_minutes=420,
                discipline="trail_running",
                technicality="high",
            )

        with self.assertRaisesRegex(ValueError, "technicité"):
            self._generate(
                name="Trail 50 km",
                event_date=date(2026, 5, 31),
                distance_km=50,
                target_time_minutes=420,
                discipline="trail_running",
                elevation_gain_m=2500,
            )

    def test_rejects_unsafe_preparation_window_and_base(self) -> None:
        with self.assertRaisesRegex(ValueError, "au moins 20 semaines"):
            self._generate(
                name="Trail 100 km",
                event_date=date(2026, 3, 15),
                distance_km=100,
                target_time_minutes=1020,
                discipline="trail_running",
                elevation_gain_m=6000,
                technicality="moderate",
            )

        low_base = build_profile()
        low_base.tolerance.usual_running_distance_per_week_km = 15
        low_base.tolerance.maximum_tolerated_weekly_distance_km = 20
        with self.assertRaisesRegex(ValueError, "base documentée"):
            TrainingProgramGenerator().generate(
                profile=low_base,
                goal=PerformanceGoal(
                    name="Trail 70 km",
                    event_date=date(2026, 7, 5),
                    distance_km=70,
                    target_time_minutes=660,
                    discipline="trail_running",
                    elevation_gain_m=4000,
                    terrain_technicality="moderate",
                ),
                start_date=self.start_date,
                settings=self.settings,
            )


if __name__ == "__main__":
    unittest.main()
