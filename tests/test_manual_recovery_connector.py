"""
Tests du bilan manuel de récupération Atlas Coach.
"""

import unittest
from datetime import date

from src.connectors.manual_recovery import (
    ManualRecoveryCheckIn,
    ManualRecoveryConnector,
)


class ManualRecoveryConnectorTests(unittest.TestCase):
    """Vérifie le fonctionnement sans capteur."""

    def setUp(self) -> None:
        self.connector = ManualRecoveryConnector()

    def test_builds_complete_manual_input(
        self,
    ) -> None:
        check_in = ManualRecoveryCheckIn(
            day=date(2026, 8, 8),
            sleep_quality_0_10=8,
            fatigue_0_10=2,
            muscle_soreness_0_10=3,
            pain_0_10=2,
            stress_0_10=2,
            sleep_hours=8,
            illness_symptoms=False,
            pain_locations=[
                "tendon.achilles.right",
            ],
            notes="Sensibilité légère au réveil.",
        )

        result = self.connector.build_input(
            check_in,
            acute_load_7d=420,
            chronic_load_28d=390,
            vo2max=51,
            vo2max_baseline=50,
        )

        self.assertEqual(
            check_in.data_quality_score,
            100,
        )
        self.assertEqual(result.sleep_hours, 8)
        self.assertEqual(
            result.sleep_quality_0_100,
            80,
        )
        self.assertEqual(
            result.subjective_fatigue_0_10,
            2,
        )
        self.assertEqual(
            result.muscle_soreness_0_10,
            3,
        )
        self.assertEqual(result.pain_0_10, 2)
        self.assertEqual(result.stress_0_10, 2)
        self.assertFalse(result.illness_symptoms)
        self.assertIn(
            "tendon.achilles.right",
            result.notes,
        )

    def test_supports_partial_check_in(
        self,
    ) -> None:
        check_in = ManualRecoveryCheckIn(
            day=date(2026, 8, 8),
            fatigue_0_10=4,
            pain_0_10=1,
        )

        result = self.connector.build_input(check_in)

        self.assertEqual(
            check_in.data_quality_score,
            40,
        )
        self.assertEqual(
            result.subjective_fatigue_0_10,
            4,
        )
        self.assertEqual(result.pain_0_10, 1)
        self.assertIsNone(result.sleep_hours)
        self.assertIsNone(
            result.sleep_quality_0_100
        )

    def test_rejects_invalid_manual_value(
        self,
    ) -> None:
        check_in = ManualRecoveryCheckIn(
            day=date(2026, 8, 8),
            pain_0_10=12,
        )

        with self.assertRaises(ValueError):
            self.connector.build_input(check_in)


if __name__ == "__main__":
    unittest.main()