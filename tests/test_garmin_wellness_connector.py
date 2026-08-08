"""
Tests du connecteur de bien-être quotidien Garmin.
"""

import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

from src.connectors.garmin_wellness import (
    DailyRecoverySnapshot,
    GarminWellnessConnector,
)


class GarminWellnessConnectorTests(unittest.TestCase):
    """Vérifie l’import et la normalisation Garmin Wellness."""

    def setUp(self) -> None:
        self.connector = GarminWellnessConnector(
            "atlas-data/garmin/wellness"
        )

    def test_builds_daily_recovery_snapshot(self) -> None:
        messages = {
            "hrv_status_summary_mesgs": [{
                "baseline_balanced_lower": 48.0,
                "baseline_balanced_upper": 62.0,
                "baseline_low_upper": 45.0,
                "last_night_5_min_high": 64.0,
                "last_night_average": 44.0,
                "status": "balanced",
                "weekly_average": 48.0,
            }],
            "sleep_assessment_mesgs": [{
                "average_stress_during_sleep": 20.14,
                "awakenings_count": 2,
                "overall_sleep_score": 81,
                "sleep_quality_score": 77,
                "sleep_recovery_score": 70,
            }],
            "monitoring_hr_data_mesgs": [
                {
                    "current_day_resting_heart_rate": 46,
                    "resting_heart_rate": 47,
                },
                {
                    "current_day_resting_heart_rate": 46,
                    "resting_heart_rate": 47,
                },
            ],
            "sleep_level_mesgs": [
                {
                    "sleep_level": "light",
                    "timestamp": datetime(
                        2026, 8, 4, 22, 28,
                        tzinfo=timezone.utc,
                    ),
                },
                {
                    "sleep_level": "deep",
                    "timestamp": datetime(
                        2026, 8, 4, 22, 57,
                        tzinfo=timezone.utc,
                    ),
                },
                {
                    "sleep_level": "awake",
                    "timestamp": datetime(
                        2026, 8, 5, 2, 10,
                        tzinfo=timezone.utc,
                    ),
                },
                {
                    "sleep_level": "rem",
                    "timestamp": datetime(
                        2026, 8, 5, 7, 16,
                        tzinfo=timezone.utc,
                    ),
                },
            ],
        }

        result = self.connector.build_snapshot(
            date(2026, 8, 5),
            messages,
        )

        self.assertEqual(result.day, date(2026, 8, 5))
        self.assertEqual(result.hrv_last_night_ms, 44.0)
        self.assertEqual(result.hrv_weekly_average_ms, 48.0)
        self.assertEqual(result.hrv_baseline_lower_ms, 48.0)
        self.assertEqual(result.hrv_baseline_upper_ms, 62.0)
        self.assertEqual(result.hrv_status, "balanced")
        self.assertEqual(result.resting_heart_rate_bpm, 46.0)
        self.assertEqual(result.sleep_score, 81)
        self.assertEqual(result.sleep_quality_score, 77)
        self.assertEqual(result.sleep_recovery_score, 70)
        self.assertEqual(result.sleep_awakenings_count, 2)
        self.assertEqual(result.sleep_average_stress, 20.14)
        self.assertEqual(len(result.sleep_levels), 4)
        self.assertEqual(result.data_quality_score, 100)
        self.assertTrue(result.hrv_available)
        self.assertTrue(result.sleep_available)

    def test_missing_optional_data_remains_supported(
        self,
    ) -> None:
        result = self.connector.build_snapshot(
            date(2026, 8, 6),
            {},
        )

        self.assertEqual(result.day, date(2026, 8, 6))
        self.assertIsNone(result.hrv_last_night_ms)
        self.assertIsNone(result.sleep_score)
        self.assertFalse(result.hrv_available)
        self.assertFalse(result.sleep_available)
        self.assertEqual(result.data_quality_score, 0)

    def test_imports_and_merges_daily_zip_archive(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            archive_path = (
                Path(temporary_directory)
                / "2026-08-05.zip"
            )

            with ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "100_HRV_STATUS.fit",
                    b"fake hrv fit",
                )
                archive.writestr(
                    "200_SLEEP_DATA.fit",
                    b"fake sleep fit",
                )
                archive.writestr(
                    "ignored.txt",
                    b"not a fit file",
                )

            def fake_merge(
                fit_path,
                destination,
            ) -> None:
                if "HRV_STATUS" in fit_path.name:
                    destination.setdefault(
                        "hrv_status_summary_mesgs",
                        [],
                    ).append({
                        "last_night_average": 44.0,
                        "weekly_average": 48.0,
                        "status": "balanced",
                    })
                if "SLEEP_DATA" in fit_path.name:
                    destination.setdefault(
                        "sleep_assessment_mesgs",
                        [],
                    ).append({
                        "overall_sleep_score": 81,
                    })

            with patch.object(
                self.connector,
                "_merge_fit_messages",
                side_effect=fake_merge,
            ) as merge_mock:
                result = self.connector.import_archive(
                    archive_path
                )

            self.assertEqual(result.day, date(2026, 8, 5))
            self.assertEqual(result.hrv_last_night_ms, 44.0)
            self.assertEqual(result.sleep_score, 81)
            self.assertEqual(merge_mock.call_count, 2)

    def test_imports_all_archives_in_chronological_order(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            wellness_directory = Path(temporary_directory)

            for archive_name in (
                "2026-08-05.zip",
                "2026-08-03.zip",
                "2026-08-04.zip",
            ):
                with ZipFile(
                    wellness_directory / archive_name,
                    "w",
                ):
                    pass

            connector = GarminWellnessConnector(
                str(wellness_directory)
            )

            def fake_import(
                archive_path,
            ) -> DailyRecoverySnapshot:
                return DailyRecoverySnapshot(
                    day=date.fromisoformat(
                        Path(archive_path).stem
                    )
                )

            with patch.object(
                connector,
                "import_archive",
                side_effect=fake_import,
            ):
                results = connector.import_all()

            self.assertEqual(
                [snapshot.day for snapshot in results],
                [
                    date(2026, 8, 3),
                    date(2026, 8, 4),
                    date(2026, 8, 5),
                ],
            )


if __name__ == "__main__":
    unittest.main()