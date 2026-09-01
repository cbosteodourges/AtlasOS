"""Tests de l'activation validée du programme 3+1 complet."""

from __future__ import annotations

import unittest

from src.training.training_program_loader import TrainingProgramLoader
from src.training.validated_program_activation import (
    CYCLE_START_DATE,
    EVENT_DATE,
    INTRO_WEEK_START,
    START_DATE,
    activate_program,
    build_validated_weeks,
)


class ValidatedProgramActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = {
            "vma_training_reference_kmh": 14.0,
            "maximum_heart_rate_bpm": 170,
            "sv1": {"speed_kmh": 10.5, "heart_rate_bpm": 138},
            "sv2": {"speed_kmh": 12.9, "heart_rate_bpm": 153},
        }
        self.active = {
            "goal": {
                "name": "Semi-marathon de Lille",
                "event_date": "2026-10-25",
                "distance_km": 21.1,
                "target_time_minutes": 109,
            },
            "athlete_snapshot": self.snapshot,
            "weeks": [{"week_number": 99, "workouts": []}],
            "warnings": [],
        }

    def test_starts_on_august_22_then_builds_nine_full_weeks(self):
        weeks = build_validated_weeks(self.snapshot)
        self.assertEqual(len(weeks), 10)
        self.assertEqual(weeks[0]["start_date"], INTRO_WEEK_START.isoformat())
        self.assertEqual(weeks[0]["end_date"], "2026-08-23")
        self.assertEqual(
            [item["workout_date"] for item in weeks[0]["workouts"]],
            ["2026-08-22", "2026-08-23"],
        )
        self.assertEqual(weeks[1]["start_date"], CYCLE_START_DATE.isoformat())
        self.assertEqual(weeks[-1]["end_date"], EVENT_DATE.isoformat())
        self.assertTrue(all(
            week["start_date"] <= week["end_date"]
            for week in weeks
        ))

    def test_first_cycle_keeps_validated_hybrid_rotation(self):
        weeks = build_validated_weeks(self.snapshot)
        saturday = [week["workouts"][5] for week in weeks[1:4]]
        self.assertEqual(
            [item["title"] for item in saturday],
            [
                "Sortie longue hybride · 3 × 8 min sous SV2",
                "Sortie longue hybride · 5 × 5 min sous SV2",
                "Sortie longue hybride · 8 × 3 min sous SV2",
            ],
        )
        self.assertEqual(
            [item["planned_duration_minutes"] for item in saturday],
            [80, 85, 90],
        )

    def test_second_cycle_reintroduces_400_and_1000_formats(self):
        weeks = build_validated_weeks(self.snapshot)
        week_five = weeks[5]["workouts"]
        titles = [item["title"] for item in week_five]
        self.assertTrue(any("400 m" in title for title in titles))
        self.assertTrue(any("1000 m" in title for title in titles))
        self.assertTrue(any("3 × 10 min" in title for title in titles))
        long_durations = [
            next(
                item["planned_duration_minutes"]
                for item in week["workouts"]
                if item["workout_type"] == "long_run"
            )
            for week in weeks[5:8]
        ]
        self.assertEqual(long_durations, [95, 100, 95])

    def test_includes_consolidation_taper_and_race_week(self):
        weeks = build_validated_weeks(self.snapshot)
        self.assertEqual(weeks[4]["phase"], "recovery")
        self.assertTrue(weeks[4]["is_recovery_week"])
        self.assertEqual(weeks[8]["phase"], "taper")
        self.assertEqual(weeks[9]["phase"], "race_week")
        race = [
            item for item in weeks[9]["workouts"]
            if item["workout_type"] == "race_specific"
        ]
        self.assertEqual(len(race), 1)
        self.assertEqual(race[0]["workout_date"], EVENT_DATE.isoformat())
        self.assertFalse(race[0]["movable"])

    def test_activation_does_not_mutate_source_and_validates_schema(self):
        original_weeks = list(self.active["weeks"])
        result = activate_program(self.active)
        self.assertEqual(self.active["weeks"], original_weeks)
        self.assertTrue(result["validated_three_plus_one"]["activated"])
        self.assertEqual(result["duration_weeks"], 10)
        workouts = TrainingProgramLoader().from_payload(result)
        self.assertEqual(len(workouts), result["total_workouts"])
        identifiers = [item.workout_id for item in workouts]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_introductory_hybrid_is_strictly_below_sv2(self):
        weeks = build_validated_weeks(self.snapshot)
        intro = weeks[0]["workouts"][0]
        target = next(
            block["target"] for block in intro["blocks"]
            if block["block_type"] == "work"
        )
        self.assertLess(target["speed_max_kmh"], self.snapshot["sv2"]["speed_kmh"])
        self.assertLess(target["heart_rate_max_bpm"], self.snapshot["sv2"]["heart_rate_bpm"])
        self.assertEqual(target["rpe_0_10"], 5.5)
        self.assertEqual(intro["title"], "Sortie longue hybride · 3 × 6 min sous SV2")

    def test_every_structured_title_has_executable_work_blocks(self):
        weeks = build_validated_weeks(self.snapshot)
        structured = [
            workout
            for week in weeks
            for workout in week["workouts"]
            if (
                "×" in workout["title"]
                or "lignes droites" in workout["title"]
            )
        ]
        self.assertGreater(len(structured), 0)
        for workout in structured:
            with self.subTest(workout=workout["workout_id"]):
                work = [
                    block
                    for block in workout["blocks"]
                    if block["block_type"] == "work"
                ]
                self.assertTrue(work)
                self.assertTrue(all(
                    int(block.get("repetitions") or 1) >= 1
                    for block in work
                ))

    def test_every_repeated_work_block_defines_recovery(self):
        weeks = build_validated_weeks(self.snapshot)
        for week in weeks:
            for workout in week["workouts"]:
                for block in workout["blocks"]:
                    if (
                        block["block_type"] == "work"
                        and int(block.get("repetitions") or 1) > 1
                    ):
                        with self.subTest(
                            workout=workout["workout_id"],
                            block=block["name"],
                        ):
                            self.assertGreater(
                                float(block.get("recovery_minutes") or 0),
                                0,
                            )

    def test_pyramid_and_descending_threshold_keep_every_transition(self):
        weeks = build_validated_weeks(self.snapshot)
        workouts = [
            workout
            for week in weeks
            for workout in week["workouts"]
        ]
        pyramid = next(
            workout
            for workout in workouts
            if workout["workout_type"] == "triangular_vo2"
        )
        pyramid_work = [
            block for block in pyramid["blocks"]
            if block["block_type"] == "work"
        ]
        self.assertEqual(
            [block["repetitions"] for block in pyramid_work],
            [2, 2, 1],
        )
        self.assertEqual(
            [block["recovery_minutes"] for block in pyramid_work],
            [1.5, 1.5, 1.5],
        )
        self.assertIn("facultative", pyramid_work[-1]["instructions"])

        descending = next(
            workout
            for workout in workouts
            if "SV2 descendant" in workout["title"]
        )
        descending_work = [
            block for block in descending["blocks"]
            if block["block_type"] == "work"
        ]
        self.assertEqual(
            [block["distance_meters"] for block in descending_work],
            [2000, 1600, 1200],
        )
        self.assertEqual(
            [block["recovery_minutes"] for block in descending_work],
            [2, 1.75, None],
        )
        self.assertIn("facultatif", descending_work[-1]["name"])

    def test_consolidation_and_race_strides_are_real_blocks(self):
        weeks = build_validated_weeks(self.snapshot)
        structured_easy = [
            workout
            for week in weeks
            for workout in week["workouts"]
            if (
                "en côte" in workout["title"]
                or "relâchées" in workout["title"]
                or "lignes droites" in workout["title"]
            )
        ]
        self.assertEqual(len(structured_easy), 3)
        for workout in structured_easy:
            with self.subTest(workout=workout["workout_id"]):
                work = next(
                    block
                    for block in workout["blocks"]
                    if block["block_type"] == "work"
                )
                self.assertGreater(work["repetitions"], 1)
                self.assertGreater(work["recovery_minutes"], 0)
                self.assertEqual(work["target"]["zone"], 5)

    def test_rejects_an_unexpected_event_date(self):
        self.active["goal"]["event_date"] = "2026-11-01"
        with self.assertRaises(ValueError):
            activate_program(self.active)


if __name__ == "__main__":
    unittest.main()
