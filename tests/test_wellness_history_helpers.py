"""Tests des jours manquants, baselines et indice Wellness."""

import json
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from datetime import date
from unittest.mock import patch
from zipfile import ZipFile

from src.connectors.garmin_wellness import (
    DailyRecoverySnapshot,
    GarminWellnessConnector,
)
from tools.atlas_web_server import (
    _atlas_recovery_index,
    _complete_wellness_calendar,
    _health_connect_wellness_by_day,
    _has_actionable_wellness,
    import_garmin_wellness_archive,
    _personal_baseline,
)


class WellnessHistoryHelpersTests(unittest.TestCase):
    def test_imports_a_dated_garmin_wellness_archive_and_refreshes_cache(self):
        archive_bytes = BytesIO()
        with ZipFile(archive_bytes, "w") as archive:
            archive.writestr("HRV_STATUS.fit", b"fit-data")
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 9, 5),
            hrv_last_night_ms=70,
            resting_heart_rate_bpm=39,
            sleep_score=91,
            data_quality_score=100,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("tools.atlas_web_server.WELLNESS_DIRECTORY", root / "archives"),
                patch("tools.atlas_web_server.WELLNESS_CACHE_PATH", root / "cache.json"),
                patch.object(GarminWellnessConnector, "import_archive", return_value=snapshot),
                patch.object(GarminWellnessConnector, "import_all_cached", return_value=[snapshot]) as refresh,
            ):
                result = import_garmin_wellness_archive(
                    "Garmin-Wellness-2026-09-05.zip",
                    archive_bytes.getvalue(),
                )

            self.assertTrue((root / "archives" / "2026-09-05.zip").is_file())
            self.assertEqual(result["hrv_last_night_ms"], 70)
            self.assertEqual(result["resting_heart_rate_bpm"], 39)
            self.assertEqual(result["fit_file_count"], 1)
            refresh.assert_called_once()

    def test_rejects_an_undated_wellness_archive(self):
        with self.assertRaisesRegex(ValueError, "AAAA-MM-JJ"):
            import_garmin_wellness_archive("wellness.zip", b"not-a-zip")

    def test_health_connect_exposes_fresh_hrv_and_resting_heart_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health-connect-wellness.json"
            path.write_text(json.dumps([
                {
                    "type": "sleep",
                    "source_id": "sleep-1",
                    "start_time": "2026-09-04T21:00:00+02:00",
                    "end_time": "2026-09-05T06:00:00+02:00",
                    "local_day": "2026-09-05",
                    "duration_seconds": 32400,
                },
                {
                    "type": "hrv_rmssd",
                    "source_id": "hrv-1",
                    "start_time": "2026-09-05T06:01:00+02:00",
                    "local_day": "2026-09-05",
                    "value": 70,
                    "source_device": "com.garmin.android.apps.connectmobile",
                },
                {
                    "type": "resting_heart_rate",
                    "source_id": "rhr-1",
                    "start_time": "2026-09-05T06:02:00+02:00",
                    "local_day": "2026-09-05",
                    "value": 39,
                },
            ]), encoding="utf-8")

            with patch(
                "tools.atlas_web_server.HEALTH_CONNECT_WELLNESS_PATH",
                path,
            ):
                result = _health_connect_wellness_by_day()["2026-09-05"]

            self.assertEqual(result["sleep_duration_minutes"], 540)
            self.assertEqual(result["hrv_last_night_ms"], 70)
            self.assertEqual(
                result["hrv_last_night_ms_source_devices"],
                ["com.garmin.android.apps.connectmobile"],
            )
            self.assertEqual(result["resting_heart_rate_bpm"], 39)
            self.assertEqual(result["hrv_last_night_ms_source"], "health_connect")
            self.assertEqual(
                result["resting_heart_rate_bpm_source"],
                "health_connect",
            )

    def test_keeps_missing_calendar_days_explicit(self):
        history = [
            {"day": "2026-08-01", "sleep_score": 80},
            {"day": "2026-08-03", "sleep_score": 82},
        ]

        complete = _complete_wellness_calendar(history)

        self.assertEqual(len(complete), 3)
        self.assertFalse(complete[1]["data_present"])
        self.assertIsNone(complete[1]["source"])

    def test_personal_baseline_uses_only_previous_days(self):
        history = [
            {"sleep_score": 70},
            {"sleep_score": 80},
            {"sleep_score": 90},
            {"sleep_score": 100},
        ]

        self.assertEqual(_personal_baseline(history, 3, "sleep_score"), 80)

    def test_training_load_contributes_to_atlas_index(self):
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 8, 5),
            sleep_score=80,
            sleep_recovery_score=75,
            hrv_last_night_ms=50,
            hrv_baseline_lower_ms=45,
            hrv_baseline_upper_ms=55,
            sleep_average_stress=20,
            data_quality_score=100,
        )

        normal = _atlas_recovery_index(
            snapshot, training_load=50, training_load_baseline=50
        )
        high = _atlas_recovery_index(
            snapshot, training_load=150, training_load_baseline=50
        )

        self.assertLess(high["score"], normal["score"])
        self.assertTrue(any(
            item["label"] == "Charge sur 7 jours" for item in high["components"]
        ))

    def test_incomplete_archive_never_creates_zero_recovery_score(self):
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 8, 22),
            hrv_weekly_average_ms=48,
            hrv_baseline_lower_ms=47,
            hrv_baseline_upper_ms=60,
            hrv_status="balanced",
            data_quality_score=0,
        )

        result = _atlas_recovery_index(
            snapshot, training_load=94, training_load_baseline=70
        )

        self.assertIsNone(result["score"])
        self.assertEqual(result["components"], [])
        self.assertFalse(_has_actionable_wellness(snapshot))

    def test_complete_sleep_snapshot_is_actionable(self):
        snapshot = DailyRecoverySnapshot(
            day=date(2026, 8, 21),
            sleep_score=73,
            sleep_recovery_score=70,
            hrv_last_night_ms=48,
            data_quality_score=80,
        )

        self.assertTrue(_has_actionable_wellness(snapshot))


if __name__ == "__main__":
    unittest.main()
