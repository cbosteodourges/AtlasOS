"""Tests du parcours de calibration des nouveaux profils Atlas."""

import unittest

from src.training.profile_calibration import profile_calibration_summary


PHYSIOLOGY = {"maximum_heart_rate_bpm": 190, "resting_heart_rate_bpm": 50}


def execution(index, domain="endurance", week=1):
    day = 1 + (week - 1) * 7 + index % 5
    return {
        "activity_id": f"activity-{week}-{index}-{domain}",
        "start_time": f"2026-01-{day:02d}T08:00:00+01:00",
        "activity": {"sport": "running", "data_quality_score": 90},
        "analysis": {
            "blocks": [{
                "block_type": domain,
                "average_speed_kmh": 10 if domain == "endurance" else 13,
                "average_heart_rate_bpm": 135 if domain == "endurance" else 165,
                "duration_seconds": 360,
            }],
        },
    }


class ProfileCalibrationTests(unittest.TestCase):
    def test_new_profile_starts_with_provisional_and_safe_program(self):
        result = profile_calibration_summary(
            [], PHYSIOLOGY, profile_exists=True, program_exists=True
        )
        self.assertEqual(result["completed_stage_count"], 2)
        self.assertEqual(result["active_stage"], 3)
        self.assertEqual(result["usable_session_count"], 0)

    def test_established_profile_requires_history_and_domain_coverage(self):
        sessions = []
        domains = ("endurance", "tempo", "threshold", "vo2")
        for week in range(1, 5):
            for index in range(3):
                sessions.append(execution(index, domains[(week + index) % 4], week))
        result = profile_calibration_summary(
            sessions, PHYSIOLOGY, profile_exists=True, program_exists=True
        )
        self.assertEqual(result["usable_session_count"], 12)
        self.assertEqual(result["covered_week_count"], 4)
        self.assertEqual(result["completed_stage_count"], 5)
        self.assertEqual(result["active_stage"], 5)

    def test_blocks_without_heart_rate_are_not_counted(self):
        item = execution(1)
        item["analysis"]["blocks"][0].pop("average_heart_rate_bpm")
        result = profile_calibration_summary(
            [item], PHYSIOLOGY, profile_exists=True, program_exists=True
        )
        self.assertEqual(result["usable_session_count"], 0)


if __name__ == "__main__":
    unittest.main()
