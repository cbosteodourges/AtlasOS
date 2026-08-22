"""Tests du protocole pilote Atlas Research 3+1."""

import unittest
from datetime import date

from src.research.norwegian_singles_catalog import (
    build_three_plus_one_pilot_registry,
)
from src.training.three_plus_one_pilot import (
    ThreePlusOnePilotPlanner,
    compare_with_active_program,
)


class ThreePlusOnePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = ThreePlusOnePilotPlanner()
        self.plan = self.planner.build(
            start_date=date(2026, 8, 24),
            wellness_status="green",
            goal_surface="road",
        )

    def test_registry_contains_subthreshold_rotations_and_microdoses(self):
        identifiers = {
            item.protocol_id
            for item in build_three_plus_one_pilot_registry().list_all()
        }
        self.assertEqual(
            identifiers,
            {
                "subthreshold_3x10",
                "subthreshold_5x6",
                "subthreshold_8_to_10x3",
                "hill_neuromuscular_sprints",
                "flat_relaxed_strides",
                "gentle_downhill_eccentric_intro",
            },
        )

    def test_builds_three_stimulus_weeks_then_consolidation(self):
        self.assertEqual(len(self.plan.weeks), 4)
        self.assertTrue(all(
            week.specific_session_count == 3
            for week in self.plan.weeks[:3]
        ))
        self.assertTrue(self.plan.weeks[3].is_consolidation)
        self.assertEqual(self.plan.weeks[3].specific_minutes, 0)

    def test_specific_stimuli_are_separated_by_48_hours(self):
        for week in self.plan.weeks[:3]:
            dates = [
                item.workout_date
                for item in week.sessions
                if item.is_specific
            ]
            gaps = [
                (current - previous).days * 24
                for previous, current in zip(dates, dates[1:])
            ]
            self.assertTrue(all(gap >= 48 for gap in gaps))

    def test_specific_minutes_stay_below_independent_cap(self):
        self.assertTrue(all(
            week.specific_minutes <= 60
            for week in self.plan.weeks[:3]
        ))

    def test_week_four_reduces_volume_and_uses_only_microdoses(self):
        week = self.plan.weeks[3]
        self.assertAlmostEqual(week.volume_factor, 0.70)
        self.assertTrue(all(
            not item.is_metabolic
            for item in week.sessions
        ))
        self.assertEqual(
            {item.protocol_id for item in week.sessions if item.protocol_id},
            {"hill_neuromuscular_sprints", "flat_relaxed_strides"},
        )

    def test_orange_reduces_specific_volume_without_raising_intensity(self):
        orange = self.planner.build(
            start_date=date(2026, 8, 24),
            wellness_status="orange",
        )
        self.assertTrue(all(
            orange_week.specific_minutes < green_week.specific_minutes
            for orange_week, green_week
            in zip(orange.weeks[:3], self.plan.weeks[:3])
        ))
        self.assertTrue(all(
            item.volume_factor == 0.75
            for week in orange.weeks[:3]
            for item in week.sessions
            if item.is_specific
        ))

    def test_red_replaces_metabolic_stimuli_with_easy_work(self):
        red = self.planner.build(
            start_date=date(2026, 8, 24),
            wellness_status="red",
        )
        self.assertTrue(all(
            week.specific_minutes == 0
            for week in red.weeks
        ))
        self.assertTrue(all(
            not item.is_metabolic
            for week in red.weeks
            for item in week.sessions
        ))

    def test_downhill_is_optional_and_reserved_for_trail(self):
        road = self.plan.weeks[3]
        trail = self.planner.build(
            start_date=date(2026, 8, 24),
            wellness_status="green",
            goal_surface="trail",
            downhill_experience=True,
        ).weeks[3]
        self.assertNotIn(
            "gentle_downhill_eccentric_intro",
            {item.protocol_id for item in road.sessions},
        )
        self.assertIn(
            "gentle_downhill_eccentric_intro",
            {item.protocol_id for item in trail.sessions},
        )

    def test_comparison_never_mutates_or_activates_active_program(self):
        active = {
            "weeks": [{
                "week_number": 1,
                "phase": "development",
                "workouts": [{
                    "workout_date": "2026-08-25",
                    "workout_type": "threshold_sv2",
                    "title": "3 × 8 min au SV2",
                    "planned_duration_minutes": 55,
                }],
            }]
        }
        comparison = compare_with_active_program(active, self.plan)
        self.assertTrue(comparison["comparison_only"])
        self.assertTrue(comparison["active_program_unchanged"])
        self.assertEqual(
            comparison["activation"]["status"],
            "not_activated",
        )
        self.assertEqual(
            comparison["active"]["weeks"][0]["specific_session_count"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
