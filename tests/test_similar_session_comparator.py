"""Tests des comparaisons strictement homogènes entre séances."""

import unittest

from src.performance import compare_with_similar_sessions


def session(sport, kind, speed, heart_rate, spread=0.2, recovery=90):
    return {
        "activity": {"sport": sport, "average_speed_kmh": speed},
        "analysis": {
            "session_type": kind,
            "blocks": [
                {"block_type": kind, "average_speed_kmh": speed - spread / 2,
                 "average_heart_rate_bpm": heart_rate},
                {"block_type": kind, "average_speed_kmh": speed + spread / 2,
                 "average_heart_rate_bpm": heart_rate},
            ],
        },
        "workout_match": {"execution": {"recovery_compliance_score": recovery}},
    }


class SimilarSessionComparatorTests(unittest.TestCase):
    def test_compares_only_same_sport_and_physiological_family(self):
        current = session("running", "vma", 14.2, 154, recovery=96)
        history = [
            session("running", "vma", 13.8, 156, recovery=88),
            session("running", "vo2", 14.0, 155, recovery=92),
            session("cycling", "vma", 32.0, 150),
            session("running", "sv2", 12.8, 151),
        ]

        result = compare_with_similar_sessions(current, history)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["sport"], "running")
        self.assertEqual(result["family"], "vo2")
        self.assertEqual(result["comparison_count"], 2)
        self.assertEqual(result["deltas"]["speed_kmh"]["difference"], 0.3)
        self.assertEqual(result["deltas"]["heart_rate_bpm"]["difference"], -1.5)

    def test_refuses_cross_sport_substitution_when_history_is_missing(self):
        current = session("running", "sv2", 12.9, 158)
        history = [
            session("cycling", "sv2", 30.0, 153),
            session("indoor_cycling", "threshold", 31.0, 154),
        ]

        result = compare_with_similar_sessions(current, history)

        self.assertEqual(result["status"], "insufficient_history")
        self.assertEqual(result["comparison_count"], 0)

    def test_leaves_unavailable_metrics_uninterpreted(self):
        current = session("running", "vma", 14.2, 154)
        current["workout_match"]["execution"].pop("recovery_compliance_score")
        history = [
            session("running", "vma", 13.9, 155),
            session("running", "vma", 14.0, 156),
        ]

        result = compare_with_similar_sessions(current, history)

        self.assertIsNone(result["deltas"]["recovery_score"])


if __name__ == "__main__":
    unittest.main()
