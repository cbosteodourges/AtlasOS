"""
Tests de la fusion des sources de récupération.
"""

import unittest

from src.physiology import PhysiologyInput
from src.physiology.recovery_fusion import (
    RecoveryFusionEngine,
)


class RecoveryFusionEngineTests(unittest.TestCase):
    """Vérifie les priorités entre capteur et utilisateur."""

    def setUp(self) -> None:
        self.engine = RecoveryFusionEngine()

    def test_fuses_sensor_and_manual_inputs(
        self,
    ) -> None:
        sensor = PhysiologyInput(
            hrv_ms=44,
            hrv_baseline_ms=48,
            resting_hr_bpm=46,
            resting_hr_baseline_bpm=47.5,
            sleep_hours=8.8,
            sleep_quality_0_100=77,
            stress_0_10=2.01,
            notes="Données Garmin.",
        )
        manual = PhysiologyInput(
            sleep_hours=8.0,
            sleep_quality_0_100=80,
            stress_0_10=4,
            subjective_fatigue_0_10=3,
            muscle_soreness_0_10=2,
            pain_0_10=2,
            illness_symptoms=False,
            notes="Achille sensible au réveil.",
        )

        result = self.engine.fuse(
            sensor_input=sensor,
            manual_input=manual,
        )
        merged = result.physiology_input

        self.assertEqual(result.mode, "hybrid")
        self.assertEqual(merged.hrv_ms, 44)
        self.assertEqual(merged.sleep_hours, 8.8)
        self.assertEqual(
            merged.sleep_quality_0_100,
            77,
        )
        self.assertEqual(merged.stress_0_10, 4)
        self.assertEqual(
            merged.subjective_fatigue_0_10,
            3,
        )
        self.assertEqual(merged.pain_0_10, 2)
        self.assertEqual(
            result.sources_by_field["sleep_hours"],
            "sensor",
        )
        self.assertEqual(
            result.sources_by_field["pain_0_10"],
            "manual",
        )
        self.assertIn("Données Garmin.", merged.notes)
        self.assertIn(
            "Achille sensible au réveil.",
            merged.notes,
        )
        self.assertTrue(result.conflicts)

    def test_supports_manual_only_mode(
        self,
    ) -> None:
        manual = PhysiologyInput(
            sleep_quality_0_100=70,
            subjective_fatigue_0_10=4,
            pain_0_10=1,
        )

        result = self.engine.fuse(
            manual_input=manual
        )

        self.assertEqual(result.mode, "manual")
        self.assertEqual(
            result.physiology_input
            .subjective_fatigue_0_10,
            4,
        )
        self.assertIsNone(
            result.physiology_input.hrv_ms
        )

    def test_supports_connected_only_mode(
        self,
    ) -> None:
        sensor = PhysiologyInput(
            hrv_ms=50,
            hrv_baseline_ms=48,
            resting_hr_bpm=45,
            resting_hr_baseline_bpm=47,
        )

        result = self.engine.fuse(
            sensor_input=sensor
        )

        self.assertEqual(result.mode, "connected")
        self.assertEqual(
            result.physiology_input.hrv_ms,
            50,
        )
        self.assertEqual(
            result.sources_by_field["hrv_ms"],
            "sensor",
        )


if __name__ == "__main__":
    unittest.main()