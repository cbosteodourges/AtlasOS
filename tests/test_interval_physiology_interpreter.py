"""Tests de la lecture physiologique prudente des fractions."""

import unittest

from src.performance import interpret_interval_physiology


def report(speeds, heart_rates, drops):
    intervals = []
    for index, speed in enumerate(speeds):
        item = {
            "duration_seconds": 180,
            "average_speed_kmh": speed,
            "average_heart_rate_bpm": heart_rates[index],
        }
        if index < len(speeds) - 1:
            item["recovery_heart_rate_drop_bpm"] = drops[index]
        intervals.append(item)
    return {
        "workout_match": {"execution": {"interval_details": intervals}},
        "analysis": {
            "session_type": "vma_long",
            "data_integrity": {"heart_rate_reliable": True},
        },
    }


class IntervalPhysiologyInterpreterTests(unittest.TestCase):
    def test_describes_a_regular_series_and_measured_recoveries(self):
        result = interpret_interval_physiology(report(
            [13.8, 13.9, 14.0, 13.9],
            [148, 151, 153, 155],
            [18, 17, 16],
        ))
        self.assertEqual(result["status"], "available")
        self.assertIn("maintenue", result["title"])
        self.assertEqual(result["metrics"]["first_to_last_heart_rate_change_bpm"], 7)
        self.assertEqual(result["metrics"]["median_recovery_heart_rate_drop_bpm"], 17)
        self.assertGreaterEqual(result["confidence"], 80)

    def test_reports_a_real_late_pace_drop_without_calling_it_fatigue(self):
        result = interpret_interval_physiology(report(
            [14.2, 14.1, 13.6], [150, 154, 158], [16, 14]
        ))
        self.assertIn("baisse d’allure", result["title"])
        self.assertTrue(any("moins rapide" in item for item in result["observations"]))
        self.assertFalse(any("fatigue" in item.lower() for item in result["observations"]))

    def test_never_invents_recovery_quality_from_missing_heart_rate(self):
        result = interpret_interval_physiology(report(
            [14.0, 14.1, 14.0], [None, None, None], [None, None]
        ))
        self.assertNotIn("median_recovery_heart_rate_drop_bpm", result["metrics"])
        self.assertTrue(any("efficacité n’est pas conclue" in item for item in result["limitations"]))

    def test_requires_at_least_two_complete_intervals(self):
        result = interpret_interval_physiology(report([14.0], [150], []))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["confidence"], 0)


if __name__ == "__main__":
    unittest.main()
