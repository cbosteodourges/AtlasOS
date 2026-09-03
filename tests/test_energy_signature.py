"""Tests de la signature énergétique personnelle Atlas."""

import unittest
from unittest.mock import patch

from tools.atlas_web_server import _energy_signature


def execution(kind, score, index, *, drift=None, competition=False):
    return {
        "start_time": f"2026-08-{index:02d}T08:00:00+02:00",
        "activity": {
            "sport": "running",
            "session_type": "race" if competition else kind,
            "data_quality_score": 90,
        },
        "analysis": {
            "session_type": kind,
            "dominant_work_type": kind,
        },
        "workout_match": {
            "execution": {
                "workout_name": "Competition 10 km" if competition else kind,
                "execution_score": score,
            }
        },
        "cardiac_drift": drift or {},
    }


class EnergySignatureTests(unittest.TestCase):
    def test_ranks_domains_from_observed_fit_sessions(self):
        sessions = [
            execution("z2", 92, 1, drift={"analyzable": True, "aerobic_decoupling_percent": 2}),
            execution("endurance", 90, 2),
            execution("tempo", 78, 3),
            execution("z3", 80, 4),
            execution("sv2", 84, 5),
            execution("threshold", 86, 6),
            execution("vma", 75, 7),
            execution("vo2", 76, 8, competition=True),
        ]
        with patch("tools.atlas_web_server.load_execution_summaries", return_value=sessions):
            result = _energy_signature()

        self.assertEqual(result["dominant_domain"], "endurance")
        self.assertEqual(result["status"], "established")
        self.assertEqual(result["competition"]["count"], 1)
        self.assertEqual(len(result["domains"]), 4)
        self.assertTrue(all(domain["session_count"] == 2 for domain in result["domains"]))

    def test_does_not_claim_a_dominant_domain_without_enough_sessions(self):
        with patch(
            "tools.atlas_web_server.load_execution_summaries",
            return_value=[execution("z2", 90, 1)],
        ):
            result = _energy_signature()

        self.assertIsNone(result["dominant_domain"])
        self.assertEqual(result["status"], "building")
        self.assertIn("hypothèses", result["cellular_interpretation"])


if __name__ == "__main__":
    unittest.main()
