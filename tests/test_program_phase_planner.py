"""Tests de planification des phases Atlas Coach."""

import unittest
from datetime import date

from src.training.program_models import TrainingPhase
from src.training.program_phase_planner import (
    ProgramPhasePlanner,
)


class ProgramPhasePlannerTests(unittest.TestCase):
    """Validation du découpage temporel de la préparation."""

    def setUp(self) -> None:
        self.planner = ProgramPhasePlanner()

    def test_builds_twelve_week_preparation(self) -> None:
        plan = self.planner.plan(
            start_date=date(2026, 6, 1),
            event_date=date(2026, 8, 23),
        )

        self.assertEqual(plan.duration_weeks, 12)
        self.assertEqual(
            plan.phase_counts,
            {
                TrainingPhase.BASE: 4,
                TrainingPhase.DEVELOPMENT: 2,
                TrainingPhase.SPECIFIC: 4,
                TrainingPhase.TAPER: 1,
                TrainingPhase.RACE_WEEK: 1,
            },
        )

    def test_preserves_progressive_phase_order(self) -> None:
        plan = self.planner.plan(
            start_date=date(2026, 6, 1),
            event_date=date(2026, 8, 23),
        )

        phase_order = list(dict.fromkeys(plan.phases))

        self.assertEqual(
            phase_order,
            [
                TrainingPhase.BASE,
                TrainingPhase.DEVELOPMENT,
                TrainingPhase.SPECIFIC,
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            ],
        )

    def test_single_week_is_race_week(self) -> None:
        plan = self.planner.plan(
            start_date=date(2026, 8, 17),
            event_date=date(2026, 8, 23),
        )

        self.assertEqual(
            plan.phases,
            [TrainingPhase.RACE_WEEK],
        )

    def test_two_weeks_include_taper_then_race_week(
        self,
    ) -> None:
        plan = self.planner.plan(
            start_date=date(2026, 8, 10),
            event_date=date(2026, 8, 23),
        )

        self.assertEqual(
            plan.phases,
            [
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            ],
        )

    def test_short_four_week_plan_remains_progressive(
        self,
    ) -> None:
        plan = self.planner.plan(
            start_date=date(2026, 7, 27),
            event_date=date(2026, 8, 23),
        )

        self.assertEqual(
            plan.phases,
            [
                TrainingPhase.DEVELOPMENT,
                TrainingPhase.SPECIFIC,
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            ],
        )

    def test_rejects_event_before_start(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "event_date ne peut pas précéder start_date",
        ):
            self.planner.plan(
                start_date=date(2026, 8, 24),
                event_date=date(2026, 8, 23),
            )


if __name__ == "__main__":
    unittest.main()