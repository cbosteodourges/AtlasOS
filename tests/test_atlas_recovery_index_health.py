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

    def test_learns_sleep_and_night_hr_from_good_training_days(self):
        end = datetime(2026, 8, 29, 6, tzinfo=timezone.utc)
        wellness = []
        outcomes = []
        for offset in range(5, 0, -1):
            previous_end = end - timedelta(days=offset)
            start = previous_end - timedelta(hours=8)
            wellness.extend([
                {
                    "type": "sleep",
                    "start_time": start.isoformat(),
                    "end_time": previous_end.isoformat(),
                    "stages": [],
                },
                {
                    "type": "heart_rate_series",
                    "samples": [{
                        "timestamp": (start + timedelta(hours=4)).isoformat(),
                        "value": 42,
                    }],
                },
            ])
            outcomes.append({
                "start_time": (previous_end + timedelta(hours=12)).isoformat(),
                "atlas_workout_match": {
                    "execution": {"execution_score": 90}
                },
            })
        current_start = end - timedelta(hours=7, minutes=28)
        wellness.extend([
            {
                "type": "sleep",
                "start_time": current_start.isoformat(),
                "end_time": end.isoformat(),
                "stages": [],
            },
            {
                "type": "heart_rate_series",
                "samples": [{
                    "timestamp": (current_start + timedelta(hours=4)).isoformat(),
                    "value": 48,
                }],
            },
        ])

        latest = AtlasRecoveryIndex().build(
            wellness, [], outcomes=outcomes
        )["latest"]
        self.assertEqual(latest["personal_sleep_target_hours"], 8.0)
        self.assertEqual(latest["personal_night_hr_target_bpm"], 42.0)
        self.assertEqual(latest["sleep_deficit_minutes"], 32)
        self.assertIn("32 min de plus", latest["guidance"])
        night_hr = next(
            item for item in latest["components"]
            if item["key"] == "night_hr"
        )
        self.assertEqual(night_hr["personal_target"], 42.0)
        self.assertLess(night_hr["score"], 50)

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



    def test_excludes_awake_stages_from_sleep_duration(self):
        end = datetime(2026, 8, 30, 6, tzinfo=timezone.utc)
        start = end - timedelta(hours=8, minutes=30)
        cursor = start
        stages = []

        for stage, minutes in (
            ("1", 59),
            ("5", 94),
            ("4", 311),
            ("6", 46),
        ):
            stage_end = cursor + timedelta(minutes=minutes)
            stages.append({
                "stage": stage,
                "start_time": cursor.isoformat(),
                "end_time": stage_end.isoformat(),
            })
            cursor = stage_end

        wellness = [{
            "type": "sleep",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "stages": stages,
        }]

        latest = AtlasRecoveryIndex().build(wellness, [])["latest"]
        duration = next(
            item for item in latest["components"]
            if item["key"] == "sleep_duration"
        )
        architecture = next(
            item for item in latest["components"]
            if item["key"] == "sleep_stages"
        )

        self.assertEqual(duration["value"], 7.52)
        self.assertEqual(duration["difference_minutes"], -29)
        self.assertEqual(architecture["deep_percent"], 21)
        self.assertEqual(architecture["rem_percent"], 10)
        self.assertEqual(architecture["awake_percent"], 12)

    def test_nap_does_not_replace_main_sleep(self):
        night_end = datetime(2026, 8, 30, 6, 40, tzinfo=timezone.utc)
        night_start = night_end - timedelta(hours=8, minutes=30)

        awake_end = night_start + timedelta(minutes=59)
        light_end = awake_end + timedelta(minutes=311)
        deep_end = light_end + timedelta(minutes=94)

        main_sleep = {
            "type": "sleep",
            "start_time": night_start.isoformat(),
            "end_time": night_end.isoformat(),
            "duration_seconds": 27060,
            "stages": [
                {
                    "stage": "1",
                    "start_time": night_start.isoformat(),
                    "end_time": awake_end.isoformat(),
                },
                {
                    "stage": "4",
                    "start_time": awake_end.isoformat(),
                    "end_time": light_end.isoformat(),
                },
                {
                    "stage": "5",
                    "start_time": light_end.isoformat(),
                    "end_time": deep_end.isoformat(),
                },
                {
                    "stage": "6",
                    "start_time": deep_end.isoformat(),
                    "end_time": night_end.isoformat(),
                },
            ],
        }

        nap_end = datetime(2026, 8, 30, 15, 0, tzinfo=timezone.utc)
        nap = {
            "type": "sleep",
            "start_time": (nap_end - timedelta(minutes=29)).isoformat(),
            "end_time": nap_end.isoformat(),
            "duration_seconds": 1740,
            "stages": [],
        }

        latest = AtlasRecoveryIndex().build(
            [main_sleep, nap],
            [],
        )["latest"]

        duration = next(
            item for item in latest["components"]
            if item["key"] == "sleep_duration"
        )

        self.assertEqual(latest["day"], "2026-08-30")
        self.assertEqual(duration["value"], 7.52)
        self.assertEqual(duration["difference_minutes"], -29)

if __name__ == "__main__":
    unittest.main()
