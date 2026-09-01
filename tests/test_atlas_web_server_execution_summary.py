import unittest

from tools.atlas_web_server import execution_summary


class AtlasWebServerExecutionSummaryTests(unittest.TestCase):
    def test_exposes_reconstructed_interval_details_to_browser(self):
        intervals = [{
            "duration_seconds": 180,
            "distance_meters": 681,
            "average_speed_kmh": 13.62,
            "recovery_duration_seconds": 79,
        }]
        private_execution = {
            "activity_id": "health-connect-2026-09-01",
            "atlas_workout_match": {
                "execution": {
                    "planned_repetition_count": 5,
                    "completed_repetition_count": 6,
                    "interval_details": intervals,
                    "private_debug_payload": "must-not-leak",
                }
            },
        }

        summary = execution_summary(private_execution)
        browser_execution = summary["workout_match"]["execution"]

        self.assertEqual(browser_execution["interval_details"], intervals)
        self.assertEqual(browser_execution["planned_repetition_count"], 5)
        self.assertEqual(browser_execution["completed_repetition_count"], 6)
        self.assertNotIn("private_debug_payload", browser_execution)


if __name__ == "__main__":
    unittest.main()
