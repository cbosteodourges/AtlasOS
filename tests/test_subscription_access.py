import unittest
from datetime import date

from src.training.subscription_access import (
    filter_program_for_subscription,
    normalize_tier,
)


class SubscriptionAccessTests(unittest.TestCase):
    def setUp(self):
        self.program = {
            "goal": {"name": "Semi"},
            "weeks": [
                {
                    "week_number": number,
                    "start_date": f"2026-0{8 + (number > 4)}-{1 + ((number - 1) % 4) * 7:02d}",
                    "end_date": f"2026-0{8 + (number > 4)}-{7 + ((number - 1) % 4) * 7:02d}",
                    "phase": "development",
                    "workouts": [{"title": f"Séance {number}"}],
                }
                for number in range(1, 9)
            ],
        }

    def test_unknown_tier_defaults_to_monthly(self):
        self.assertEqual(normalize_tier("unknown"), "monthly")

    def test_founder_receives_every_week(self):
        result = filter_program_for_subscription(
            self.program, "founder_admin", date(2026, 8, 1)
        )
        self.assertEqual(len(result["weeks"]), 8)
        self.assertTrue(result["access_control"]["full_access"])
        self.assertEqual(result["locked_weeks"], [])

    def test_annual_receives_every_week(self):
        result = filter_program_for_subscription(
            self.program, "annual", date(2026, 8, 1)
        )
        self.assertEqual(len(result["weeks"]), 8)
        self.assertTrue(result["access_control"]["can_print_full_program"])

    def test_monthly_receives_four_rolling_weeks(self):
        result = filter_program_for_subscription(
            self.program, "monthly", date(2026, 8, 1)
        )
        self.assertEqual(len(result["weeks"]), 4)
        self.assertEqual(len(result["locked_weeks"]), 4)
        self.assertNotIn("workouts", result["locked_weeks"][0])
        self.assertEqual(result["locked_weeks"][0]["unlock_date"], "2026-08-11")

    def test_expired_receives_no_future_details(self):
        result = filter_program_for_subscription(
            self.program, "expired", date(2026, 8, 1)
        )
        self.assertEqual(result["weeks"], [])
        self.assertEqual(len(result["locked_weeks"]), 8)


if __name__ == "__main__":
    unittest.main()
