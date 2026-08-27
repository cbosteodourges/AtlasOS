import tempfile
import unittest
from pathlib import Path

from src.connectors import ActivityStore, NormalizedActivity, merge_activities


def activity(provider="strava", external_id="1", samples=None, metadata=None):
    return NormalizedActivity(provider=provider, external_id=external_id,
        activity_type="run", start_time="2026-08-25T18:00:12Z",
        duration_seconds=3600, distance_meters=10000,
        samples=samples or [], raw_metadata=metadata or {})


class ActivityIngestionTests(unittest.TestCase):
    def test_same_session_from_two_sources_is_merged(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ActivityStore(Path(directory) / "activities.json")
            result = store.ingest([activity(), activity("garmin", "fit-1")])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].source_ids, {"strava": "1", "garmin": "fit-1"})

    def test_detailed_fit_has_priority(self):
        fit = activity("garmin", "fit-1", metadata={"source_file": "a.fit", "laps": [{"x": 1}]})
        fit.average_heart_rate_bpm = 151
        strava = activity()
        strava.average_heart_rate_bpm = 149
        merged = merge_activities(strava, fit)
        self.assertEqual(merged.provider, "garmin")
        self.assertEqual(merged.average_heart_rate_bpm, 151)

    def test_reimport_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ActivityStore(Path(directory) / "activities.json")
            store.ingest([activity()])
            self.assertEqual(len(store.ingest([activity()])), 1)


if __name__ == "__main__":
    unittest.main()
