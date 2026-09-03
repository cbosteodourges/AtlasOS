"""Tests du moteur de progression par famille de séances."""

import unittest

from src.performance.session_family_progression import (
    build_all_family_progressions,
    build_endurance_progression,
    build_tempo_progression,
    build_threshold_progression,
    build_vo2_progression,
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


def intensity_session(index, kind, speed, heart_rate, work_minutes=18, repetitions=3):
    block_type = {"tempo": "z3", "threshold": "sv2", "vo2": "vma"}[kind]
    duration = work_minutes * 60 / repetitions
    return {
        "start_time": f"2026-{index:02d}-10T18:00:00+02:00",
        "activity": {
            "sport": "running", "session_type": block_type,
            "data_quality_score": 92,
        },
        "analysis": {
            "session_type": block_type, "dominant_work_type": block_type,
            "data_integrity": {
                "heart_rate_reliable": True,
                "physiological_data_usable": True,
            },
            "blocks": [{
                "block_type": block_type,
                "duration_seconds": duration,
                "average_speed_kmh": speed,
                "average_heart_rate_bpm": heart_rate,
            } for _ in range(repetitions)],
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

    def test_builds_tempo_and_threshold_from_work_blocks_only(self):
        tempo = [
            intensity_session(index, "tempo", speed, 148)
            for index, speed in enumerate((11.0, 11.1, 11.2, 11.5, 11.6, 11.7), 1)
        ]
        threshold = [
            intensity_session(index, "threshold", speed, 160, work_minutes=15)
            for index, speed in enumerate((12.3, 12.4, 12.5, 12.8, 12.9, 13.0), 1)
        ]

        tempo_result = build_tempo_progression(tempo)
        threshold_result = build_threshold_progression(threshold)

        self.assertEqual(tempo_result["trend"], "up")
        self.assertEqual(threshold_result["trend"], "up")
        self.assertEqual(threshold_result["reference_heart_rate_bpm"], 160)
        self.assertEqual(threshold_result["recent"]["work_speed_kmh"], 12.9)

    def test_vo2_uses_repetition_speed_and_keeps_heart_rate_contextual(self):
        sessions = [
            intensity_session(index, "vo2", speed, heart_rate, work_minutes=8, repetitions=8)
            for index, (speed, heart_rate) in enumerate((
                (13.8, 166), (13.9, 168), (14.0, 169),
                (14.2, 167), (14.3, 170), (14.4, 171),
            ), 1)
        ]

        result = build_vo2_progression(sessions)

        self.assertTrue(result["available"])
        self.assertEqual(result["trend"], "up")
        self.assertEqual(result["early"]["heart_rate_bpm"], 168)
        self.assertIn("FC reste contextuelle", result["method"])

    def test_rejects_specific_session_without_detected_work_blocks(self):
        missing_blocks = intensity_session(1, "threshold", 12.8, 160)
        missing_blocks["analysis"]["blocks"] = []

        result = build_threshold_progression([missing_blocks])

        self.assertEqual(result["session_count"], 0)
        self.assertEqual(result["exclusion_reasons"]["blocs de travail absents"], 1)

    def test_prepares_all_four_families_without_ui_dependency(self):
        sessions = [session(1, 10.0)] + [
            intensity_session(2, family, speed, heart_rate)
            for family, speed, heart_rate in (
                ("tempo", 11.4, 148),
                ("threshold", 12.8, 160),
                ("vo2", 14.2, 170),
            )
        ]

        result = build_all_family_progressions(sessions)

        self.assertEqual(set(result), {"endurance", "tempo", "threshold", "vo2"})


if __name__ == "__main__":
    unittest.main()
