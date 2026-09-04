"""Tests de la signature énergétique personnelle Atlas."""

import unittest
from unittest.mock import patch

from tools.atlas_web_server import _energy_signature


REFERENCES = {"vma_kmh": 16, "sv1_speed_kmh": 10, "sv2_speed_kmh": 13}


def execution(kind, index, *, speed=10, support=2400, execution_score=90, quality=90,
              competition=False, day=None):
    return {
        "start_time": f"2026-08-{day or index:02d}T08:00:00+02:00",
        "activity": {"sport": "running", "session_type": "race" if competition else kind,
                     "data_quality_score": quality, "average_speed_kmh": speed,
                     "duration_minutes": support / 60},
        "analysis": {"session_type": kind, "dominant_work_type": kind,
                     "work_duration_seconds": support,
                     "blocks": [{"block_type": kind, "average_speed_kmh": speed,
                                 "duration_seconds": support}]},
        "workout_match": {"execution": {
            "workout_name": "Competition 10 km" if competition else kind,
            "execution_score": execution_score,
        }},
        "cardiac_drift": {},
    }


class EnergySignatureTests(unittest.TestCase):
    def signature(self, sessions):
        enough = len(sessions) >= 3
        weekly = {
            "week": "2026-S36",
            "domains": {
                key: {
                    "trend": "en progression" if enough else None,
                    "heart_rate_delta_bpm": -3 if enough else None,
                    "confidence": 70 if enough else 0,
                    "interpretation": "À allure comparable, la FC récente varie de -3,0 bpm." if enough else "Données insuffisantes.",
                }
                for key in ("endurance", "tempo", "threshold", "vo2")
            },
        }
        with (
            patch("tools.atlas_web_server.load_execution_summaries", return_value=sessions),
            patch("tools.atlas_web_server.load_physiological_reference", return_value=REFERENCES),
            patch("tools.atlas_web_server.weekly_heart_rate_speed_profile", return_value=weekly),
        ):
            return _energy_signature()

    def test_describes_four_domains_from_observed_physiology(self):
        sessions = []
        settings = {"z2": (10.2, 3000), "tempo": (11.5, 1500),
                    "sv2": (12.8, 1200), "vma": (15.4, 720)}
        index = 1
        for kind, (speed, support) in settings.items():
            for _ in range(4):
                sessions.append(execution(kind, index, speed=speed, support=support,
                                          competition=(kind == "vma" and index == 13)))
                index += 1
        result = self.signature(sessions)

        self.assertEqual(result["status"], "established")
        self.assertEqual(result["competition"]["count"], 1)
        self.assertEqual(len(result["domains"]), 4)
        self.assertTrue(all(domain["session_count"] == 4 for domain in result["domains"]))
        for field in ("support_capacity", "regularity", "evidence", "validity"):
            self.assertTrue(all(field in domain for domain in result["domains"]))

    def test_execution_compliance_never_changes_physiological_index(self):
        low = self.signature([execution("tempo", 1, speed=11.5, support=1200,
                                        execution_score=20)])
        high = self.signature([execution("tempo", 1, speed=11.5, support=1200,
                                         execution_score=100)])
        low_tempo = next(item for item in low["domains"] if item["key"] == "tempo")
        high_tempo = next(item for item in high["domains"] if item["key"] == "tempo")
        self.assertEqual(low_tempo["score"], high_tempo["score"])

    def test_uses_weekly_heart_rate_speed_trend(self):
        sessions = [execution("tempo", index, speed=11.5, support=1200)
                    for index in range(1, 7)]
        tempo = next(item for item in self.signature(sessions)["domains"] if item["key"] == "tempo")
        self.assertEqual(tempo["trend"], "en progression")
        self.assertEqual(tempo["trend_delta"], -3)

    def test_does_not_claim_a_dominant_domain_without_enough_sessions(self):
        result = self.signature([execution("z2", 1)])
        self.assertIsNone(result["dominant_domain"])
        self.assertEqual(result["status"], "building")
        self.assertIn("hypothèses", result["cellular_interpretation"])


if __name__ == "__main__":
    unittest.main()
