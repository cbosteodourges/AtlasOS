import unittest
from datetime import datetime, timedelta, timezone

from src.connectors.activity_schema import NormalizedActivity
from src.physiology.atlas_recovery_index import AtlasRecoveryIndex


class AtlasRecoveryIndexHealthTests(unittest.TestCase):
    def test_builds_transparent_score_without_inventing_hrv(self):
        end = datetime(2026, 8, 27, 6, tzinfo=timezone.utc)
        start = end - timedelta(hours=8)
        wellness = [{
            "type": "sleep", "start_time": start.isoformat(), "end_time": end.isoformat(),
            "stages": [{"stage": "5", "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=1.5)).isoformat()},
                       {"stage": "6", "start_time": (start + timedelta(hours=1.5)).isoformat(),
                        "end_time": (start + timedelta(hours=3.5)).isoformat()}],
        }, {"type": "resting_heart_rate", "start_time": end.isoformat(), "value": 48}]
        result = AtlasRecoveryIndex().build(wellness, [])
        self.assertIsNotNone(result["latest"])
        self.assertFalse(result["latest"]["hrv_used"])
        self.assertNotIn("hrv", {item["key"] for item in result["latest"]["components"]})

    def test_compares_sleep_duration_with_personal_history(self):
        end = datetime(2026, 8, 29, 6, tzinfo=timezone.utc)
        wellness = []
        for offset in range(5, 0, -1):
            previous_end = end - timedelta(days=offset)
            wellness.append({
                "type": "sleep",
                "start_time": (previous_end - timedelta(hours=8)).isoformat(),
                "end_time": previous_end.isoformat(),
                "stages": [],
            })
        wellness.append({
            "type": "sleep",
            "start_time": (end - timedelta(hours=7, minutes=28)).isoformat(),
            "end_time": end.isoformat(),
            "stages": [],
        })

        latest = AtlasRecoveryIndex().build(wellness, [])["latest"]
        duration = next(
            item for item in latest["components"]
            if item["key"] == "sleep_duration"
        )
        self.assertEqual(duration["personal_target_hours"], 8.0)
        self.assertEqual(duration["difference_minutes"], -32)
        self.assertLess(duration["score"], 90)
        self.assertLess(latest["confidence"], 100)

    def test_uses_real_rmssd_and_recent_load_when_available(self):
        end = datetime(2026, 8, 27, 6, tzinfo=timezone.utc)
        wellness = [{"type": "sleep", "start_time": (end - timedelta(hours=8)).isoformat(),
                     "end_time": end.isoformat(), "stages": []},
                    {"type": "hrv_rmssd", "start_time": end.isoformat(), "value": 52}]
        activities = [NormalizedActivity(provider="strava", external_id=str(day), activity_type="run",
                      start_time=(end - timedelta(days=day)).isoformat(), duration_seconds=2400)
                      for day in range(1, 15)]
        latest = AtlasRecoveryIndex().build(wellness, activities)["latest"]
        keys = {item["key"] for item in latest["components"]}
        self.assertTrue(latest["hrv_used"])
        self.assertIn("hrv", keys)
        self.assertIn("training_load", keys)


if __name__ == "__main__":
    unittest.main()
