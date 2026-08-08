"""
Tests du calcul de l’Indice ATLAS.
"""

import unittest

from src.atlas_brain.atlas_index import (
    AtlasIndexEngine,
)
from src.physiology.physiology_engine import (
    PhysiologyResult,
)


class AtlasIndexEngineTests(unittest.TestCase):
    """Vérifie le calcul global et les plafonds de sécurité."""

    def setUp(self) -> None:
        self.engine = AtlasIndexEngine()

    @staticmethod
    def physiology_result(
        *,
        recovery: float = 68.8,
        readiness: float = 68.8,
        confidence: float = 71.6,
        alerts: list[str] | None = None,
    ) -> PhysiologyResult:
        return PhysiologyResult(
            recovery_score=recovery,
            fatigue_score=100.0 - recovery,
            readiness_score=readiness,
            sleep_score=90.8,
            autonomic_score=44.6,
            load_score=50.0,
            data_confidence=confidence,
            status="DISPONIBLE",
            risk_level="FAIBLE_A_MODERE",
            recommendation="Intensité contrôlée.",
            alerts=alerts or [],
            explanations=[],
            metrics={},
        )

    def test_uses_physiology_when_biomechanics_missing(
        self,
    ) -> None:
        result = self.engine.calculate(
            self.physiology_result()
        )

        self.assertEqual(result.score, 69)
        self.assertEqual(result.status, "DISPONIBLE")
        self.assertEqual(result.recovery_score, 69)
        self.assertEqual(
            result.training_readiness_score,
            69,
        )
        self.assertIsNone(
            result.biomechanical_tolerance_score
        )
        self.assertEqual(result.data_confidence_score, 72)

    def test_combines_physiology_and_biomechanics(
        self,
    ) -> None:
        result = self.engine.calculate(
            self.physiology_result(
                recovery=82,
                readiness=80,
                confidence=90,
            ),
            mechanical_risk_score=20,
            mechanical_data_confidence=80,
        )

        self.assertEqual(result.score, 80)
        self.assertEqual(result.status, "OPTIMAL")
        self.assertEqual(
            result.biomechanical_tolerance_score,
            80,
        )
        self.assertEqual(result.data_confidence_score, 87)

    def test_high_mechanical_risk_caps_index(
        self,
    ) -> None:
        result = self.engine.calculate(
            self.physiology_result(
                recovery=90,
                readiness=90,
                confidence=90,
            ),
            mechanical_risk_score=75,
            mechanical_data_confidence=90,
        )

        self.assertEqual(result.score, 35)
        self.assertEqual(result.status, "ADAPTER")
        self.assertEqual(
            result.biomechanical_tolerance_score,
            25,
        )

    def test_safety_alert_caps_index(
        self,
    ) -> None:
        result = self.engine.calculate(
            self.physiology_result(
                recovery=90,
                readiness=90,
                confidence=90,
                alerts=["Symptômes de maladie signalés."],
            ),
            mechanical_risk_score=10,
            mechanical_data_confidence=90,
        )

        self.assertEqual(result.score, 30)
        self.assertEqual(result.status, "RECUPERATION")
        self.assertEqual(
            result.alerts,
            ["Symptômes de maladie signalés."],
        )


if __name__ == "__main__":
    unittest.main()