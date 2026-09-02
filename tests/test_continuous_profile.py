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

    def test_strong_quality_session_proposes_immediate_vo2_gain_only(self):
        start = datetime.now(timezone.utc)
        samples = []
        for offset in range(0, 181, 10):
            samples.append(ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=13.7 / 3.6,
                heart_rate_bpm=150,
            ))
        for offset in range(190, 281, 10):
            samples.append(ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=14.6 / 3.6,
                heart_rate_bpm=158,
            ))
        activity = NormalizedActivity(
            provider="health_connect",
            external_id="quality-session",
            activity_type="run",
            start_time=start.isoformat(),
            duration_seconds=1800,
            average_speed_mps=11 / 3.6,
            average_heart_rate_bpm=140,
            samples=samples,
        )
        current = {
            "vo2_max": 50,
            "vma_kmh": 14,
            "sv1": {"speed_kmh": 10.5, "heart_rate_bpm": 138},
            "sv2": {"speed_kmh": 12.9, "heart_rate_bpm": 160},
        }
        result = ContinuousPhysiologyEstimator().estimate([activity], current)
        self.assertEqual(result["vo2_max"], 51)
        self.assertEqual(result["decision"], "increase_candidate")
        self.assertTrue(result["observed"]["fast_vo2_signal"])
        self.assertEqual(result["sv1"]["speed_kmh"], 10.5)
        self.assertEqual(result["sv2"]["speed_kmh"], 12.9)

        confirmed = ContinuousPhysiologyEstimator().estimate(
            [activity], {**current, "vo2_max": 51}
        )
        self.assertEqual(confirmed["vo2_max"], 51)
        self.assertFalse(confirmed["observed"]["fast_vo2_signal"])

    def test_fast_signal_uses_latest_session_not_historical_maximum(self):
        now = datetime.now(timezone.utc)

        def quality_activity(identifier, start, long_speed, short_speed):
            samples = [
                ActivitySample(
                    timestamp=start + timedelta(seconds=offset),
                    speed_mps=long_speed / 3.6,
                    heart_rate_bpm=150,
                )
                for offset in range(0, 181, 10)
            ]
            samples.extend(
                ActivitySample(
                    timestamp=start + timedelta(seconds=offset),
                    speed_mps=short_speed / 3.6,
                    heart_rate_bpm=158,
                )
                for offset in range(190, 281, 10)
            )
            return NormalizedActivity(
                provider="health_connect",
                external_id=identifier,
                activity_type="run",
                start_time=start.isoformat(),
                duration_seconds=1800,
                average_speed_mps=11 / 3.6,
                average_heart_rate_bpm=140,
                samples=samples,
            )

        old = quality_activity("old", now - timedelta(days=30), 16.4, 16.5)
        latest = quality_activity("latest", now, 13.7, 14.6)
        result = ContinuousPhysiologyEstimator().estimate(
            [latest, old], {"vo2_max": 50.3, "vma_kmh": 14}
        )

        self.assertEqual(result["vo2_max"], 51)
        self.assertLess(
            result["observed"]["strongest_session"]["three_minutes_kmh"],
            15,
        )


if __name__ == "__main__":
    unittest.main()
