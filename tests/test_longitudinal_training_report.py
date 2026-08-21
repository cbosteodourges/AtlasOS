"""Tests du rapport physiologique argumenté Atlas."""

import unittest
from unittest.mock import patch

from tools.atlas_web_server import _longitudinal_training_report


class LongitudinalTrainingReportTests(unittest.TestCase):
    def test_builds_evidenced_conclusions_without_inventing_vo2max(self):
        executions = []
        for index in range(6):
            executions.append({
                "start_time": f"2026-07-{1 + index * 7:02d}T08:00:00+02:00",
                "workout_match": {"workout_id": f"workout-{index}"},
                "activity": {
                    "sport": "running",
                    "distance_km": 10 + index,
                    "average_speed_kmh": 10 + index * 0.1,
                    "average_heart_rate_bpm": 140,
                },
                "analysis": {
                    "session_type": "endurance",
                    "data_integrity": {"heart_rate_reliable": True},
                    "threshold_observations": [],
                },
            })

        with patch(
            "tools.atlas_web_server.load_execution_summaries",
            return_value=executions,
        ), patch(
            "tools.atlas_web_server.load_workout_contexts",
            return_value=[],
        ):
            report = _longitudinal_training_report([{"day": "2026-08-01"}])

        topics = {item["topic"] for item in report["conclusions"]}
        self.assertIn("Volume et fréquence", topics)
        self.assertIn("Relation allure / fréquence cardiaque", topics)
        self.assertTrue(all(
            0 <= item["confidence"] <= 100
            and item["evidence"]
            for item in report["conclusions"]
        ))
        self.assertTrue(any("VO₂max" in item for item in report["missing_data"]))


if __name__ == "__main__":
    unittest.main()
