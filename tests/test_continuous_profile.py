import unittest
from datetime import datetime, timedelta, timezone

from src.connectors.activity_schema import ActivitySample, NormalizedActivity
from src.physiology.continuous_profile import ContinuousPhysiologyEstimator


class ContinuousProfileTests(unittest.TestCase):
    def activity(self, speed=4.0, heart_rate=158):
        samples = [ActivitySample(timestamp=str(i), speed_mps=speed, heart_rate_bpm=heart_rate)
                   for i in range(240)]
        return NormalizedActivity(provider="strava", external_id="1", activity_type="run",
            start_time=datetime.now(timezone.utc).isoformat(), duration_seconds=1800,
            average_speed_mps=speed * .85, average_heart_rate_bpm=heart_rate, samples=samples)

    def test_updates_quickly_but_bounds_daily_change(self):
        current = {"vo2_max": 51, "vma_kmh": 14, "maximum_heart_rate_bpm": 170,
                   "sv1": {"speed_kmh": 10.6, "heart_rate_bpm": 138},
                   "sv2": {"speed_kmh": 13.03, "heart_rate_bpm": 160}}
        result = ContinuousPhysiologyEstimator().estimate([self.activity(), self.activity()], current)
        self.assertTrue(result["updated"])
        self.assertLessEqual(abs(result["vma_kmh"] - 14), .2)
        self.assertLessEqual(abs(result["vo2_max"] - 51), .701)
        self.assertEqual(result["maximum_heart_rate_bpm"], 170)

    def test_excludes_unconfirmed_heart_rate_above_170(self):
        current = {"vma_kmh": 14, "maximum_heart_rate_bpm": 170,
                   "sv1": {"speed_kmh": 10.6, "heart_rate_bpm": 138},
                   "sv2": {"speed_kmh": 13.03, "heart_rate_bpm": 160}}
        result = ContinuousPhysiologyEstimator().estimate([self.activity(heart_rate=176)] * 2, current)
        self.assertEqual(result["sv2"]["heart_rate_bpm"], 160)

    def test_sparse_health_connect_samples_use_elapsed_time(self):
        start = datetime.now(timezone.utc)
        samples = [
            ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=14.2 / 3.6,
                heart_rate_bpm=150,
            )
            for offset in range(0, 181, 10)
        ]
        activity = NormalizedActivity(
            provider="health_connect",
            external_id="sparse",
            activity_type="run",
            start_time=start.isoformat(),
            duration_seconds=1800,
            average_speed_mps=10 / 3.6,
            average_heart_rate_bpm=130,
            samples=samples,
        )
        result = ContinuousPhysiologyEstimator().estimate(
            [activity] * 3,
            {"vo2_max": 50, "vma_kmh": 14},
        )
        self.assertTrue(result["updated"])
        self.assertEqual(result["observed"]["vma_kmh"], 14.2)

    def test_does_not_lower_validated_references_from_easy_sessions(self):
        current = {
            "vo2_max": 50,
            "vma_kmh": 14,
            "sv1": {"speed_kmh": 10.5, "heart_rate_bpm": 138},
            "sv2": {"speed_kmh": 12.9, "heart_rate_bpm": 160},
            "maximum_heart_rate_bpm": 170,
        }
        result = ContinuousPhysiologyEstimator().estimate(
            [self.activity(speed=3.6, heart_rate=150)] * 4,
            current,
        )
        self.assertEqual(result["vo2_max"], 50)
        self.assertEqual(result["vma_kmh"], 14)
        self.assertEqual(result["sv1"]["speed_kmh"], 10.5)
        self.assertEqual(result["sv2"]["speed_kmh"], 12.9)
        self.assertLessEqual(result["confidence"], .90)


if __name__ == "__main__":
    unittest.main()
