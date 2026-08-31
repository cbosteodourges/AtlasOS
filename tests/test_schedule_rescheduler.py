import unittest
from datetime import date

from src.training.schedule_rescheduler import reschedule_workout


class ScheduleReschedulerTests(unittest.TestCase):
    def program(self):
        return {
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2026-08-24",
                    "end_date": "2026-08-30",
                    "workouts": [
                        {
                            "workout_id": "easy",
                            "workout_date": "2026-08-24",
                            "title": "Endurance Z2",
                            "workout_type": "endurance",
                        },
                        {
                            "workout_id": "vo2",
                            "workout_date": "2026-08-25",
                            "title": "8 × 400 m VO2",
                            "workout_type": "vo2max",
                        },
                        {
                            "workout_id": "threshold",
                            "workout_date": "2026-08-27",
                            "title": "3 × 8 min SV2",
                            "workout_type": "threshold",
                        },
                        {
                            "workout_id": "long",
                            "workout_date": "2026-08-29",
                            "title": "Sortie longue hybride",
                            "workout_type": "long_run",
                        },
                    ],
                },
                {
                    "week_number": 2,
                    "start_date": "2026-08-31",
                    "end_date": "2026-09-06",
                    "workouts": [
                        {
                            "workout_id": "easy-2",
                            "workout_date": "2026-09-01",
                            "title": "Endurance facile",
                            "workout_type": "endurance",
                        },
                        {
                            "workout_id": "threshold-2",
                            "workout_date": "2026-09-03",
                            "title": "Séance SV2",
                            "workout_type": "threshold",
                        },
                    ],
                },
            ]
        }

    def workouts(self, result):
        return {
            workout["workout_id"]: (week_index, workout)
            for week_index, week in enumerate(result["program"]["weeks"])
            for workout in week["workouts"]
        }

    def assert_hard_sessions_are_spaced(self, workouts):
        hard_ids = ("vo2", "threshold", "long", "threshold-2")
        hard_dates = sorted(
            date.fromisoformat(workouts[key][1]["workout_date"])
            for key in hard_ids
        )
        for first, second in zip(hard_dates, hard_dates[1:]):
            self.assertGreaterEqual((second - first).days, 2)

    def test_requested_move_is_kept_and_conflicts_are_shifted(self):
        result = reschedule_workout(
            self.program(),
            "vo2",
            "2026-08-26",
        )
        workouts = self.workouts(result)

        self.assertEqual(
            workouts["vo2"][1]["workout_date"],
            "2026-08-26",
        )
        self.assert_hard_sessions_are_spaced(workouts)
        self.assertGreater(len(result["changes"]), 1)

    def test_easy_move_does_not_rewrite_quality_sessions(self):
        result = reschedule_workout(
            self.program(),
            "easy",
            "2026-08-26",
        )
        self.assertEqual(len(result["changes"]), 1)

    def test_move_to_next_week_changes_week_container(self):
        result = reschedule_workout(
            self.program(),
            "vo2",
            "2026-09-02",
        )
        workouts = self.workouts(result)

        self.assertEqual(workouts["vo2"][0], 1)
        self.assertEqual(
            workouts["vo2"][1]["workout_date"],
            "2026-09-02",
        )
        self.assert_hard_sessions_are_spaced(workouts)
        self.assertIn(
            "autre semaine",
            result["summary"],
        )

    def test_past_easy_session_can_be_recovered_next_week(self):
        result = reschedule_workout(
            self.program(),
            "easy",
            "2026-09-02",
        )
        workouts = self.workouts(result)

        self.assertEqual(workouts["easy"][0], 1)
        self.assertEqual(
            workouts["easy"][1]["workout_date"],
            "2026-09-02",
        )
        self.assertEqual(
            workouts["easy"][1]["rescheduled_from"],
            "2026-08-24",
        )

    def test_user_can_move_only_selected_session(self):
        result = reschedule_workout(
            self.program(),
            "long",
            "2026-08-31",
            rebalance=False,
        )
        workouts = self.workouts(result)

        self.assertEqual(
            workouts["long"][1]["workout_date"],
            "2026-08-31",
        )
        self.assertEqual(
            workouts["vo2"][1]["workout_date"],
            "2026-08-25",
        )
        self.assertEqual(
            workouts["threshold-2"][1]["workout_date"],
            "2026-09-03",
        )
        self.assertEqual(len(result["changes"]), 1)

    def test_user_can_replace_easy_session_on_target_day(self):
        result = reschedule_workout(
            self.program(),
            "long",
            "2026-09-01",
            rebalance=False,
            replace_target_easy=True,
        )
        workouts = self.workouts(result)

        self.assertNotIn("easy-2", workouts)
        self.assertEqual(
            workouts["long"][1]["workout_date"],
            "2026-09-01",
        )
        self.assertEqual(
            workouts["vo2"][1]["workout_date"],
            "2026-08-25",
        )
        self.assertEqual(
            workouts["threshold-2"][1]["workout_date"],
            "2026-09-03",
        )
        self.assertEqual(len(result["removed_workouts"]), 1)
        self.assertEqual(
            result["removed_workouts"][0]["workout_id"],
            "easy-2",
        )

    def test_date_outside_program_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "programme actif",
        ):
            reschedule_workout(
                self.program(),
                "vo2",
                "2026-09-10",
            )


if __name__ == "__main__":
    unittest.main()