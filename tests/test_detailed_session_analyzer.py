"""
Tests de l'analyse détaillée des séances FIT.
"""

import unittest
from datetime import datetime, timedelta

from src.connectors import ActivitySample
from src.performance import (
    AthleteProfile,
    DetailedSessionAnalyzer,
    LongitudinalActivity,
)
from src.performance.athlete_profile import (
    PhysiologicalReferences,
)


class DetailedSessionAnalyzerTests(unittest.TestCase):
    """Vérifie la détection des blocs d'une séance."""

    def setUp(self) -> None:
        self.analyzer = DetailedSessionAnalyzer()
        self.start = datetime.fromisoformat(
            "2026-08-02T08:30:00+02:00"
        )
        self.profile = AthleteProfile(
            athlete_id="athlete-test",
            declared_level="intermediate",
            observed_level="intermediate",
            physiological=PhysiologicalReferences(
                maximum_heart_rate_bpm=180,
                threshold_heart_rate_bpm=160,
                vma_kmh=14,
                threshold_speed_kmh=12.8,
            ),
        )

    def _sample(
        self,
        seconds: int,
        speed_mps: float,
        distance_meters: float,
        heart_rate_bpm: float,
    ) -> ActivitySample:
        return ActivitySample(
            timestamp=(
                self.start
                + timedelta(seconds=seconds)
            ).isoformat(),
            speed_mps=speed_mps,
            distance_meters=distance_meters,
            heart_rate_bpm=heart_rate_bpm,
            cadence_spm=170,
            power_watts=350,
            ground_contact_time_ms=250,
            vertical_ratio_percent=8.5,
        )

    def test_detects_z2_acceleration_and_recovery(
        self,
    ) -> None:
        samples = [
            self._sample(0, 2.8, 0, 130),
            self._sample(10, 2.8, 28, 132),
            self._sample(20, 2.8, 56, 133),
            self._sample(30, 2.8, 84, 134),
            self._sample(40, 2.8, 112, 135),
            self._sample(50, 2.8, 140, 136),
            self._sample(60, 3.3, 173, 142),
            self._sample(70, 4.0, 213, 153),
            self._sample(80, 4.5, 258, 165),
            self._sample(90, 2.0, 278, 145),
            self._sample(100, 2.0, 298, 138),
            self._sample(110, 2.0, 318, 134),
            self._sample(120, 2.0, 338, 130),
            self._sample(130, 2.0, 358, 128),
            self._sample(140, 2.0, 378, 126),
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:detailed-test",
            start_time=self.start,
            activity_type="running",
            distance_km=0.378,
            duration_minutes=140 / 60,
            samples=samples,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        block_types = [
            block.block_type
            for block in result.blocks
        ]

        self.assertIn("z2", block_types)
        self.assertIn("acceleration", block_types)
        self.assertIn("recovery", block_types)
        self.assertGreater(
            result.physiological_load_score,
            0,
        )
        self.assertGreater(
            result.analysis_confidence_score,
            0,
        )


if __name__ == "__main__":
    unittest.main()