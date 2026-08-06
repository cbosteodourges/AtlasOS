"""
Tests de l'évolution longitudinale des seuils physiologiques.
"""

import unittest
from datetime import datetime, timedelta

from src.performance import (
    AthleteProfile,
    DetailedSessionAnalysis,
    ThresholdEvolutionAnalyzer,
    ThresholdObservation,
)
from src.performance.athlete_profile import (
    PhysiologicalReferences,
)


class ThresholdEvolutionAnalyzerTests(unittest.TestCase):
    """Vérifie que plusieurs séances font évoluer les seuils."""

    def setUp(self) -> None:
        self.analyzer = ThresholdEvolutionAnalyzer()
        self.start = datetime.fromisoformat(
            "2026-08-01T08:00:00+02:00"
        )
        self.profile = AthleteProfile(
            athlete_id="athlete-threshold-test",
            declared_level="intermediate",
            observed_level="intermediate",
            physiological=PhysiologicalReferences(
                maximum_heart_rate_bpm=180,
                threshold_heart_rate_bpm=160,
                vma_kmh=14,
                threshold_speed_kmh=12.8,
            ),
        )

    def _analysis(
        self,
        index: int,
        sv1_speed: float,
        sv1_hr: float,
        sv2_speed: float,
        sv2_hr: float,
    ) -> DetailedSessionAnalysis:
        return DetailedSessionAnalysis(
            activity_id=f"activity-{index}",
            threshold_observations=[
                ThresholdObservation(
                    threshold_name="sv1",
                    estimated_speed_kmh=sv1_speed,
                    estimated_heart_rate_bpm=sv1_hr,
                    confidence_score=78,
                    evidence=["Transition Z2 vers Z3."],
                ),
                ThresholdObservation(
                    threshold_name="sv2",
                    estimated_speed_kmh=sv2_speed,
                    estimated_heart_rate_bpm=sv2_hr,
                    confidence_score=82,
                    evidence=["Transition Z3 vers SV2."],
                ),
            ],
        )

    def test_updates_thresholds_from_concordant_sessions(
        self,
    ) -> None:
        analyses = [
            self._analysis(1, 10.4, 140, 12.7, 159),
            self._analysis(2, 10.5, 141, 12.8, 160),
            self._analysis(3, 10.6, 142, 12.9, 161),
            self._analysis(4, 10.5, 141, 12.8, 160),
        ]

        result = self.analyzer.update(
            self.profile,
            analyses,
            updated_at=self.start,
        )

        self.assertEqual(
            result.physiological.sv1.observation_count,
            4,
        )
        self.assertEqual(
            result.physiological.sv2.observation_count,
            4,
        )
        self.assertAlmostEqual(
            result.physiological.sv1.speed_kmh,
            10.5,
            places=1,
        )
        self.assertAlmostEqual(
            result.physiological.sv2.speed_kmh,
            12.8,
            places=1,
        )
        self.assertGreaterEqual(
            result.physiological.sv1.confidence_score,
            70,
        )
        self.assertGreaterEqual(
            result.physiological.sv2.confidence_score,
            70,
        )
        self.assertEqual(
            len(result.physiological.sv1.history),
            1,
        )
        self.assertEqual(
            len(result.physiological.sv2.history),
            1,
        )


    def test_does_not_update_from_isolated_session(
        self,
    ) -> None:
        analyses = [
            self._analysis(
                1,
                10.8,
                145,
                13.2,
                164,
            )
        ]

        result = self.analyzer.update(
            self.profile,
            analyses,
            updated_at=(
                self.start + timedelta(days=1)
            ),
        )

        self.assertIsNone(
            result.physiological.sv1.speed_kmh
        )
        self.assertIsNone(
            result.physiological.sv2.speed_kmh
        )
        self.assertEqual(
            result.physiological
            .threshold_speed_kmh,
            12.8,
        )
        self.assertEqual(
            result.physiological
            .threshold_heart_rate_bpm,
            160,
        )

if __name__ == "__main__":
    unittest.main()