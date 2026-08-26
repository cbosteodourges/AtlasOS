import unittest

from src.training.schedule_rescheduler import reschedule_workout


class ScheduleReschedulerTests(unittest.TestCase):
    def program(self):
        return {"weeks": [{"week_number": 1, "workouts": [
            {"workout_id": "easy", "workout_date": "2026-08-24", "title": "Endurance Z2", "workout_type": "endurance"},
            {"workout_id": "vo2", "workout_date": "2026-08-25", "title": "8 × 400 m VO2", "workout_type": "vo2max"},
            {"workout_id": "threshold", "workout_date": "2026-08-27", "title": "3 × 8 min SV2", "workout_type": "threshold"},
            {"workout_id": "long", "workout_date": "2026-08-29", "title": "Sortie longue hybride", "workout_type": "long_run"},
        ]}]}

    def test_requested_move_is_kept_and_conflicting_quality_is_shifted(self):
        result = reschedule_workout(self.program(), "vo2", "2026-08-26")
        workouts = {
            item["workout_id"]: item
            for item in result["program"]["weeks"][0]["workouts"]
        }
        self.assertEqual(workouts["vo2"]["workout_date"], "2026-08-26")
        hard_dates = sorted(
            workouts[key]["workout_date"] for key in ("vo2", "threshold", "long")
        )
        for first, second in zip(hard_dates, hard_dates[1:]):
            from datetime import date
            self.assertGreaterEqual(
                (date.fromisoformat(second) - date.fromisoformat(first)).days,
                2,
            )
        self.assertGreater(len(result["changes"]), 1)

    def test_easy_move_does_not_rewrite_quality_sessions(self):
        result = reschedule_workout(self.program(), "easy", "2026-08-26")
        self.assertEqual(len(result["changes"]), 1)

    def test_move_outside_current_week_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "même semaine"):
            reschedule_workout(self.program(), "vo2", "2026-09-02")


if __name__ == "__main__":
    unittest.main()
