import tempfile
import unittest
from pathlib import Path

from src.connectors import (
    ActivitySample,
    ActivityStore,
    NormalizedActivity,
    merge_activities,
)


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

    def test_same_source_id_replaces_corrected_distance(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ActivityStore(Path(directory) / "activities.json")
            wrong = activity(
                "health_connect",
                "exercise-1",
            )
            wrong.distance_meters = 15655
            store.ingest([wrong])

            corrected = activity(
                "health_connect",
                "exercise-1",
            )
            corrected.distance_meters = 10548
            result = store.ingest([corrected])

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].distance_meters, 10548)
            self.assertEqual(
                result[0].source_ids["health_connect"],
                "exercise-1",
            )

    def test_health_connect_is_primary_and_fit_enriches_samples(self):
        health = activity(
            "health_connect",
            "exercise-1",
            samples=[
                ActivitySample(
                    timestamp="2026-08-25T18:00:12Z",
                    heart_rate_bpm=130,
                ),
            ],
        )
        health.average_heart_rate_bpm = 130
        fit = activity(
            "garmin",
            "fit-1",
            samples=[
                ActivitySample(
                    timestamp=(
                        f"2026-08-25T18:00:{second:02d}Z"
                    ),
                    speed_mps=3.0,
                )
                for second in range(10, 20)
            ],
            metadata={
                "source_file": "a.fit",
                "laps": [{"x": 1}],
            },
        )
        fit.average_heart_rate_bpm = 151

        merged = merge_activities(fit, health)

        self.assertEqual(merged.provider, "health_connect")
        self.assertEqual(merged.average_heart_rate_bpm, 130)
        self.assertEqual(len(merged.samples), 10)
        self.assertEqual(
            merged.field_provenance["samples"],
            "garmin_fit",
        )
        self.assertEqual(merged.raw_metadata["laps"], [{"x": 1}])


    def test_strava_enriches_health_connect_without_replacing_totals(self):
        health = activity(
            "health_connect",
            "exercise-1",
            samples=[
                ActivitySample(
                    timestamp="2026-08-25T18:00:12Z",
                    heart_rate_bpm=130,
                ),
            ],
        )
        health.distance_meters = 10540
        strava = activity(
            "strava",
            "strava-1",
            samples=[
                ActivitySample(
                    timestamp=f"2026-08-25T18:00:{second:02d}Z",
                    speed_mps=3.0,
                )
                for second in range(10, 20)
            ],
        )
        strava.distance_meters = 10548
        strava.elevation_gain_m = 132

        merged = merge_activities(strava, health)

        self.assertEqual(merged.provider, "health_connect")
        self.assertEqual(merged.distance_meters, 10540)
        self.assertEqual(merged.elevation_gain_m, 132)
        self.assertEqual(len(merged.samples), 10)
        self.assertEqual(
            merged.field_provenance["samples"],
            "strava",
        )

    def test_reimport_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ActivityStore(Path(directory) / "activities.json")
            store.ingest([activity()])
            self.assertEqual(len(store.ingest([activity()])), 1)


if __name__ == "__main__":
    unittest.main()
