"""Tests du profil hebdomadaire allure–fréquence cardiaque."""

import unittest
from datetime import date, timedelta

from src.training.heart_rate_speed_profile import (
    weekly_heart_rate_speed_profile,
    weekly_threshold_state_profile,
)


PHYSIOLOGY = {
    "resting_heart_rate_bpm": 45,
    "maximum_heart_rate_bpm": 170,
    "sv1_speed_kmh": 10.5,
    "sv1_heart_rate_bpm": 138,
    "sv2_speed_kmh": 12.9,
    "sv2_heart_rate_bpm": 153,
    "vma_kmh": 14,
    "vo2_max": 51,
}


def session(day, heart_rate, *, speed=12.6, kind="sv2", index=1):
    return {
        "activity_id": f"fit-{day}-{index}",
        "start_time": f"{day.isoformat()}T18:00:00+02:00",
        "activity": {"sport": "running", "data_quality_score": 95, "temperature_c": 14},
        "analysis": {"data_integrity": {"heart_rate_reliable": True}, "blocks": [{
            "block_type": kind,
            "average_speed_kmh": speed,
            "average_heart_rate_bpm": heart_rate,
            "duration_seconds": 480,
        }]},
    }


class HeartRateSpeedProfileTests(unittest.TestCase):
    def test_detects_lower_heart_rate_at_the_same_speed(self):
        as_of = date(2026, 9, 4)
        executions = []
        for offset, hr in ((100, 159), (90, 158), (80, 160), (20, 155), (12, 154), (4, 155)):
            executions.append(session(as_of - timedelta(days=offset), hr, index=offset))

        result = weekly_heart_rate_speed_profile(executions, PHYSIOLOGY, as_of=as_of)
        threshold = result["domains"]["threshold"]

        self.assertEqual(threshold["trend"], "en progression")
        self.assertLessEqual(threshold["heart_rate_delta_bpm"], -3)
        self.assertGreater(threshold["projected_speed_kmh"], 12.9)
        self.assertEqual(threshold["recent_session_count"], 3)
        self.assertEqual(threshold["baseline_session_count"], 3)

    def test_refuses_a_conclusion_from_one_session(self):
        as_of = date(2026, 9, 4)
        executions = [
            session(as_of - timedelta(days=90), 160, index=1),
            session(as_of - timedelta(days=5), 154, index=2),
        ]
        threshold = weekly_heart_rate_speed_profile(executions, PHYSIOLOGY, as_of=as_of)["domains"]["threshold"]
        self.assertIsNone(threshold["trend"])
        self.assertIsNone(threshold["projected_speed_kmh"])

    def test_ignores_unreliable_heart_rate(self):
        item = session(date(2026, 9, 1), 150)
        item["analysis"]["data_integrity"]["heart_rate_reliable"] = False
        result = weekly_heart_rate_speed_profile([item], PHYSIOLOGY, as_of=date(2026, 9, 4))
        self.assertEqual(result["domains"]["threshold"]["recent_block_count"], 0)

    def test_projects_speed_and_hr_as_a_threshold_pair(self):
        as_of = date(2026, 9, 4)
        executions = []
        for offset, hr in ((100, 159), (90, 158), (80, 160), (20, 155), (12, 154), (4, 155)):
            executions.append(session(as_of - timedelta(days=offset), hr, index=offset))

        state = weekly_threshold_state_profile(
            executions, PHYSIOLOGY, as_of=as_of
        )["states"]["sv2"]

        self.assertTrue(state["usable"])
        self.assertEqual(state["direction"], "progression")
        self.assertGreater(state["projection"]["speed_kmh"], 12.9)
        self.assertEqual(state["projection"]["heart_rate_bpm"], 155)
        self.assertEqual(state["projection"]["heart_rate_percent_max"], 91.2)
        self.assertGreaterEqual(state["threshold_specific_sessions"], 2)

    def test_does_not_infer_sv1_hr_from_generic_warmups(self):
        as_of = date(2026, 9, 4)
        executions = []
        for offset, hr in ((100, 140), (90, 140), (20, 132), (10, 132)):
            executions.append(session(
                as_of - timedelta(days=offset), hr,
                speed=10.0, kind="warmup", index=offset,
            ))

        state = weekly_threshold_state_profile(
            executions, PHYSIOLOGY, as_of=as_of
        )["states"]["sv1"]

        self.assertEqual(state["projection"]["heart_rate_bpm"], 138)
        self.assertEqual(state["threshold_specific_sessions"], 0)


if __name__ == "__main__":
    unittest.main()
