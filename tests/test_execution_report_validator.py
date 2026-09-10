"""Tests de la barrière de sécurité des comptes rendus Atlas."""

import unittest

from src.performance import validate_execution_report


def report():
    return {
        "activity": {"duration_minutes": 10},
        "workout_match": {"execution": {
            "completed_repetition_count": 2,
            "interval_details": [
                {"start_seconds": 60, "end_seconds": 240,
                 "duration_seconds": 180, "average_speed_kmh": 14,
                 "average_heart_rate_bpm": 150, "recovery_seconds": 120},
                {"start_seconds": 360, "end_seconds": 540,
                 "duration_seconds": 180, "average_speed_kmh": 14.1,
                 "average_heart_rate_bpm": 154},
            ],
        }},
        "analysis": {
            "data_integrity": {"heart_rate_reliable": True},
            "blocks": [{"start_offset_seconds": 0, "end_offset_seconds": 600}],
        },
    }


class ExecutionReportValidatorTests(unittest.TestCase):
    def test_accepts_a_complete_consistent_report(self):
        result = validate_execution_report(report())
        self.assertEqual(result["status"], "valid")
        self.assertTrue(result["safe_for_interpretation"])
        self.assertTrue(all(result["capabilities"].values()))

    def test_blocks_interpretation_when_interval_count_is_inconsistent(self):
        payload = report()
        payload["workout_match"]["execution"]["completed_repetition_count"] = 3
        result = validate_execution_report(payload)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["safe_for_interpretation"])
        self.assertFalse(result["capabilities"]["interval_count"])

    def test_blocks_interpretation_when_timeline_exceeds_activity(self):
        payload = report()
        payload["analysis"]["blocks"][0]["end_offset_seconds"] = 640
        result = validate_execution_report(payload)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["capabilities"]["timeline"])

    def test_detects_a_gap_between_displayed_phases(self):
        payload = report()
        payload["analysis"]["blocks"] = [
            {"start_offset_seconds": 0, "end_offset_seconds": 240},
            {"start_offset_seconds": 300, "end_offset_seconds": 600},
        ]
        result = validate_execution_report(payload)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["capabilities"]["timeline"])

    def test_disables_only_the_conclusion_whose_metric_is_missing(self):
        payload = report()
        payload["workout_match"]["execution"]["interval_details"][1].pop(
            "average_heart_rate_bpm"
        )
        result = validate_execution_report(payload)
        self.assertTrue(result["safe_for_interpretation"])
        self.assertTrue(result["capabilities"]["speed_regularity"])
        self.assertFalse(result["capabilities"]["heart_rate_evolution"])

    def test_declared_missing_heart_rate_overrides_stale_interval_values(self):
        payload = report()
        payload["analysis"]["data_integrity"].update({
            "heart_rate_available": False,
            "heart_rate_reliable": False,
        })

        result = validate_execution_report(payload)

        self.assertTrue(result["safe_for_interpretation"])
        self.assertTrue(result["capabilities"]["speed_regularity"])
        self.assertFalse(result["capabilities"]["heart_rate_evolution"])
        self.assertFalse(result["capabilities"]["recovery_interpretation"])


if __name__ == "__main__":
    unittest.main()
