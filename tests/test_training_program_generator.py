"""Tests de génération complète du programme Atlas Coach."""

import unittest
from datetime import date, timedelta

from src.performance.athlete_profile import (
    AthleteProfile,
    PhysiologicalReferences,
    TrainingAvailability,
    TrainingTolerance,
)
from src.performance.models import PerformanceGoal
from src.training.program_generator import (
    TrainingProgramGenerator,
)
from src.training.program_models import (
    ProgramGenerationSettings,
    TrainingPhase,
)
from src.training.session_models import WorkoutType


def build_profile(
    *,
    pain: bool = False,
    available_days: int = 5,
    with_metrics: bool = True,
) -> AthleteProfile:
    """Construit un profil longitudinal réaliste."""
    physiological = PhysiologicalReferences()

    if with_metrics:
        physiological.vma_kmh = 14.0
        physiological.threshold_speed_kmh = 13.0

    return AthleteProfile(
        athlete_id="athlete-test",
        declared_level="competitive",
        observed_level="competitive",
        physiological=physiological,
        availability=TrainingAvailability(
            available_days_per_week=available_days,
        ),
        tolerance=TrainingTolerance(
            usual_running_distance_per_week_km=35,
            usual_running_sessions_per_week=4,
            maximum_tolerated_weekly_distance_km=45,
            learned_physiological_tolerance_score=75,
            learned_biomechanical_tolerance_score=78,
            learned_response_count=12,
        ),
        current_pain_or_injury=pain,
        pain_or_injury_notes=(
            "Douleur achilléenne"
            if pain
            else ""
        ),
        history_activity_count=300,
        history_duration_weeks=100,
        data_quality_score=92,
        profile_confidence_score=90,
    )


def build_goal() -> PerformanceGoal:
    """Construit l’objectif de référence."""
    return PerformanceGoal(
        name="10 km objectif",
        event_date=date(2026, 8, 23),
        distance_km=10.0,
        target_time_minutes=47,
    )


def build_settings(
    running_sessions: int = 4,
) -> ProgramGenerationSettings:
    """Construit des préférences simples pour les tests."""
    return ProgramGenerationSettings(
        running_sessions_per_week=running_sessions,
        strength_sessions_per_week=1,
        preferred_long_run_day="sunday",
        preferred_quality_days=["tuesday", "friday"],
        include_mobility=True,
    )


class TrainingProgramGeneratorTests(unittest.TestCase):
    """Validation de la chaîne profil → programme."""

    def setUp(self) -> None:
        self.generator = TrainingProgramGenerator()
        self.start_date = date(2026, 6, 1)

    def test_generates_complete_twelve_week_program(
        self,
    ) -> None:
        program = self.generator.generate(
            profile=build_profile(),
            goal=build_goal(),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )

        self.assertEqual(program.duration_weeks, 12)
        self.assertEqual(
            program.settings.running_sessions_per_week,
            4,
        )
        self.assertEqual(
            program.settings
            .optional_running_sessions_per_week,
            1,
        )
        self.assertEqual(
            program.weeks[0].start_date,
            self.start_date,
        )
        self.assertEqual(
            program.weeks[-1].end_date,
            build_goal().event_date,
        )
        self.assertGreater(
            program.total_running_workouts,
            0,
        )
        self.assertFalse(
            any(
                "recovery_status" in warning
                for warning in program.warnings
            )
        )

    def test_uses_all_progressive_phases(self) -> None:
        program = self.generator.generate(
            profile=build_profile(),
            goal=build_goal(),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )

        self.assertEqual(
            list(dict.fromkeys(
                week.phase
                for week in program.weeks
            )),
            [
                TrainingPhase.BASE,
                TrainingPhase.DEVELOPMENT,
                TrainingPhase.SPECIFIC,
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            ],
        )

    def test_integrates_and_rotates_research_protocols(
        self,
    ) -> None:
        program = self.generator.generate(
            profile=build_profile(),
            goal=build_goal(),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )
        research_types = {
            workout.workout_type
            for week in program.weeks
            for workout in week.workouts
            if workout.workout_type in {
                WorkoutType.HILL_SPRINTS,
                WorkoutType.MIXED_THRESHOLD_VO2,
                WorkoutType.TRIANGULAR_VO2,
            }
        }

        self.assertEqual(
            research_types,
            {
                WorkoutType.HILL_SPRINTS,
                WorkoutType.MIXED_THRESHOLD_VO2,
                WorkoutType.TRIANGULAR_VO2,
            },
        )

    def test_places_race_once_on_event_date(self) -> None:
        goal = build_goal()
        program = self.generator.generate(
            profile=build_profile(),
            goal=goal,
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )
        races = [
            workout
            for week in program.weeks
            for workout in week.workouts
            if (
                workout.workout_type
                == WorkoutType.RACE_SPECIFIC
            )
        ]

        self.assertEqual(len(races), 1)
        self.assertEqual(
            races[0].workout_date,
            goal.event_date,
        )
        self.assertEqual(
            races[0].planned_distance_km,
            10.0,
        )
        self.assertEqual(
            program.weeks[-1].running_workout_count,
            3,
        )

    def test_respects_running_availability(self) -> None:
        program = self.generator.generate(
            profile=build_profile(available_days=2),
            goal=build_goal(),
            start_date=self.start_date,
            settings=build_settings(running_sessions=4),
            available_dynamic_metrics={"recovery_status"},
        )

        self.assertTrue(
            all(
                week.running_workout_count <= 2
                for week in program.weeks
            )
        )

    def test_active_pain_creates_initial_recovery_week(
        self,
    ) -> None:
        program = self.generator.generate(
            profile=build_profile(pain=True),
            goal=build_goal(),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )
        first_week = program.weeks[0]

        self.assertEqual(
            first_week.phase,
            TrainingPhase.RECOVERY,
        )
        self.assertEqual(
            first_week.running_workout_count,
            0,
        )
        self.assertEqual(
            {
                workout.workout_type
                for workout in first_week.workouts
            },
            {WorkoutType.MOBILITY},
        )
        self.assertTrue(program.warnings)

    def test_missing_metrics_remain_explainable(
        self,
    ) -> None:
        program = self.generator.generate(
            profile=build_profile(with_metrics=False),
            goal=build_goal(),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )

        self.assertTrue(
            any(
                "Mesures manquantes" in warning
                for warning in program.warnings
            )
        )

    def test_requested_strength_sessions_are_scheduled(
        self,
    ) -> None:
        program = self.generator.generate(
            profile=build_profile(),
            goal=build_goal(),
            start_date=self.start_date,
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )
        workout_types = {
            workout.workout_type
            for week in program.weeks
            for workout in week.workouts
        }

        self.assertIn(
            WorkoutType.STRENGTH,
            workout_types,
        )
        self.assertNotIn(
            WorkoutType.MOBILITY,
            workout_types,
        )
    def test_calendar_weeks_run_monday_to_sunday(
        self,
    ) -> None:
        program = self.generator.generate(
            profile=build_profile(),
            goal=build_goal(),
            start_date=date(2026, 8, 8),
            settings=build_settings(),
            available_dynamic_metrics={"recovery_status"},
        )
        first_week = program.weeks[0]

        self.assertEqual(
            first_week.start_date,
            date(2026, 8, 3),
        )
        self.assertEqual(
            first_week.end_date,
            date(2026, 8, 9),
        )
        self.assertTrue(
            all(
                workout.workout_date
                >= date(2026, 8, 8)
                for workout in first_week.workouts
            )
        )
        self.assertEqual(
            program.weeks[-1].end_date,
            build_goal().event_date,
        )

    def test_spreads_easy_sessions_across_week(
        self,
    ) -> None:
        monday = date(2026, 8, 10)
        dates = [
            monday + timedelta(days=index)
            for index in range(7)
        ]

        result = self.generator._spread_dates(
            dates,
            4,
        )

        self.assertEqual(
            result,
            [
                date(2026, 8, 10),
                date(2026, 8, 12),
                date(2026, 8, 14),
                date(2026, 8, 16),
            ],
        )
    def test_rejects_too_many_optional_sessions(
        self,
    ) -> None:
        settings = build_settings()
        settings.optional_running_sessions_per_week = 3

        with self.assertRaisesRegex(
            ValueError,
            "optional_running_sessions_per_week",
        ):
            self.generator.generate(
                profile=build_profile(),
                goal=build_goal(),
                start_date=self.start_date,
                settings=settings,
            )

if __name__ == "__main__":
    unittest.main()
