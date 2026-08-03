"""Tests du connecteur d'historique Garmin ATLAS OS."""

import csv
import tempfile
import unittest
from pathlib import Path

from src.connectors import (
    GarminHistoryConnector,
    NormalizedActivity,
)


class GarminHistoryConnectorTests(unittest.TestCase):
    """Vérifie l'importation du CSV Garmin Connect."""

    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.csv_path = (
            Path(self.temporary_directory.name)
            / "Activities.csv"
        )

        headers = [
            "Type d'activité",
            "Date",
            "Favori",
            "Titre",
            "Distance",
            "Calories",
            "Durée",
            "Fréquence cardiaque moyenne",
            "Fréquence cardiaque maximale",
            "TE aérobie",
            "Cadence de course moyenne",
            "Cadence de course moyenne",
            "Allure moyenne",
            "Meilleure allure",
            "Ascension totale",
            "Consommation du Body Battery",
            "Temps de déplacement",
            "Temps écoulé",
            "Training Stress Score® (TSS®)",
        ]

        row = [
            "Course à pied",
            "2026-08-02 19:51:44",
            "false",
            "Course du soir",
            "6.55",
            "617",
            "00:43:58",
            "134",
            "159",
            "2.9",
            "168",
            "170",
            "6:43",
            "5:20",
            "131",
            "'-7",
            "00:43:54",
            "00:44:10",
            "42.5",
        ]

        with self.csv_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)
            writer.writerow(row)

    def test_connect_requires_existing_file(self) -> None:
        connector = GarminHistoryConnector(
            "historique-inexistant.csv"
        )

        with self.assertRaises(FileNotFoundError):
            connector.connect()

    def test_import_and_normalize_activity(self) -> None:
        connector = GarminHistoryConnector(
            str(self.csv_path)
        )
        connector.connect()

        raw_activities = list(
            connector.fetch_activities()
        )
        activity = connector.normalize(
            raw_activities[0]
        )

        self.assertEqual(len(raw_activities), 1)
        self.assertIsInstance(
            activity,
            NormalizedActivity,
        )
        self.assertEqual(
            activity.activity_type,
            "running",
        )
        self.assertEqual(
            activity.distance_meters,
            6550.0,
        )
        self.assertEqual(
            activity.duration_seconds,
            2638.0,
        )
        self.assertEqual(
            activity.calories_kcal,
            617.0,
        )
        self.assertEqual(
            activity.average_heart_rate_bpm,
            134.0,
        )
        self.assertEqual(
            activity.maximum_heart_rate_bpm,
            159.0,
        )
        self.assertEqual(
            activity.elevation_gain_m,
            131.0,
        )
        self.assertEqual(
            activity.training_load,
            42.5,
        )
        self.assertEqual(
            activity.raw_metadata[
                "aerobic_training_effect"
            ],
            2.9,
        )
        self.assertEqual(
            activity.raw_metadata[
                "body_battery_consumption"
            ],
            -7.0,
        )

    def test_since_filter_excludes_old_activity(self) -> None:
        connector = GarminHistoryConnector(
            str(self.csv_path)
        )
        connector.connect()

        activities = list(
            connector.fetch_activities(
                since="2026-08-03T00:00:00+02:00"
            )
        )

        self.assertEqual(activities, [])

    def test_duplicate_headers_are_renamed(self) -> None:
        headers = GarminHistoryConnector._unique_headers(
            [
                "Cadence",
                "Cadence",
                "Cadence",
            ]
        )

        self.assertEqual(
            headers,
            [
                "Cadence",
                "Cadence__2",
                "Cadence__3",
            ],
        )

    def test_number_parser_handles_garmin_values(self) -> None:
        self.assertEqual(
            GarminHistoryConnector._parse_number(
                "'-7"
            ),
            -7.0,
        )
        self.assertEqual(
            GarminHistoryConnector._parse_number(
                "1,234"
            ),
            1234.0,
        )
        self.assertIsNone(
            GarminHistoryConnector._parse_number(
                "--"
            )
        )


if __name__ == "__main__":
    unittest.main()