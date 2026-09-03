"""Tests du moteur de progression par famille de séances."""

import unittest

from src.performance.session_family_progression import (
    build_endurance_progression,
)


def session(index, speed, heart_rate=130, *, kind="z2", elevation=35, quality=90):
    return {
        "start_time": f"2026-{index:02d}-01T08:00:00+02:00",
        "activity": {
            "sport": "running",
            "session_type": kind,
            "duration_minutes": 50,
            "distance_km": 8,
            "average_speed_kmh": speed,
            "average_heart_rate_bpm": heart_rate,
            "elevation_gain_m": elevation,
            "data_quality_score": quality,
        },
        "analysis": {
            "session_type": kind,
            "dominant_work_type": kind,
            "data_integrity": {"heart_rate_reliable": True},
        },
        "cardiac_drift": {
            "analyzable": True,
            "aerobic_decoupling_percent": 2.5,
        },
    }


class SessionFamilyProgressionTests(unittest.TestCase):
    def test_detects_endurance_progression_at_comparable_heart_rate(self):
        sessions = [
            session(1, 9.8), session(2, 9.9), session(3, 10.0),
            session(4, 10.4), session(5, 10.5), session(6, 10.6),
        ]
        result = build_endurance_progression(sessions)

        self.assertTrue(result["available"])
        self.assertEqual(result["trend"], "up")
        self.assertGreater(result["trend_percent"], 4)
        self.assertEqual(result["reference_heart_rate_bpm"], 130)
        self.assertEqual(result["session_count"], 6)

    def test_excludes_other_families_hills_and_unreliable_heart_rate(self):
        sessions = [
            session(1, 10.0, kind="tempo"),
            session(2, 10.0, elevation=200),
            session(3, 10.0),
        ]
        sessions[2]["analysis"]["data_integrity"]["heart_rate_reliable"] = False
        result = build_endurance_progression(sessions)

        self.assertFalse(result["available"])
        self.assertEqual(result["session_count"], 0)
        self.assertEqual(result["excluded"], 2)

    def test_requires_four_comparable_sessions_before_claiming_a_trend(self):
        result = build_endurance_progression([
            session(1, 10.0), session(2, 10.3), session(3, 10.5),
        ])

        self.assertFalse(result["available"])
        self.assertEqual(result["trend"], "insufficient")
        self.assertIsNone(result["trend_percent"])


if __name__ == "__main__":
    unittest.main()
