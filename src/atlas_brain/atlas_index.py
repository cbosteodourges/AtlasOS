"""
ATLAS OS
Calcul explicable de l’Indice ATLAS quotidien.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from src.physiology.physiology_engine import (
    PhysiologyResult,
)


@dataclass(slots=True)
class AtlasIndexResult:
    """Indice global transmis à Atlas Coach et Atlas Brain."""

    score: int
    status: str
    recovery_score: int
    training_readiness_score: int
    biomechanical_tolerance_score: Optional[int]
    data_confidence_score: int
    alerts: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Retourne une représentation sérialisable."""
        return asdict(self)


class AtlasIndexEngine:
    """Fusionne physiologie et tolérance biomécanique."""

    VERSION = "1.0.0"

    PHYSIOLOGY_WEIGHT = 0.70
    BIOMECHANICS_WEIGHT = 0.30

    def calculate(
        self,
        physiology: PhysiologyResult,
        *,
        mechanical_risk_score: Optional[float] = None,
        mechanical_data_confidence: Optional[float] = None,
    ) -> AtlasIndexResult:
        """Calcule l’Indice ATLAS sur 100."""
        readiness = self._clamp(
            physiology.readiness_score
        )
        recovery = self._clamp(
            physiology.recovery_score
        )

        tolerance = None
        score = readiness
        confidence = self._clamp(
            physiology.data_confidence
        )

        explanations = [
            (
                "Disponibilité physiologique : "
                f"{round(readiness)}/100."
            ),
            (
                "Récupération physiologique : "
                f"{round(recovery)}/100."
            ),
        ]

        if mechanical_risk_score is not None:
            mechanical_risk = self._clamp(
                mechanical_risk_score
            )
            tolerance = 100.0 - mechanical_risk

            score = (
                readiness * self.PHYSIOLOGY_WEIGHT
                + tolerance * self.BIOMECHANICS_WEIGHT
            )

            mechanical_confidence = self._clamp(
                mechanical_data_confidence
                if mechanical_data_confidence is not None
                else 50.0
            )
            confidence = (
                confidence * self.PHYSIOLOGY_WEIGHT
                + mechanical_confidence
                * self.BIOMECHANICS_WEIGHT
            )

            explanations.append(
                "Tolérance biomécanique : "
                f"{round(tolerance)}/100."
            )

            if mechanical_risk >= 70:
                score = min(score, 35.0)
                explanations.append(
                    "L’Indice ATLAS est plafonné par un "
                    "risque biomécanique élevé."
                )
            elif mechanical_risk >= 50:
                score = min(score, 55.0)
                explanations.append(
                    "L’Indice ATLAS est limité par la "
                    "tolérance biomécanique."
                )
        else:
            explanations.append(
                "Tolérance biomécanique non disponible : "
                "indice provisoirement fondé sur la physiologie."
            )

        alerts = list(physiology.alerts)

        if alerts:
            score = min(score, 30.0)
            explanations.append(
                "Une alerte de sécurité plafonne "
                "l’Indice ATLAS."
            )

        final_score = round(self._clamp(score))
        status = self._status(final_score)

        explanations.append(
            f"Indice ATLAS {final_score}/100 : {status}."
        )

        return AtlasIndexResult(
            score=final_score,
            status=status,
            recovery_score=round(recovery),
            training_readiness_score=round(readiness),
            biomechanical_tolerance_score=(
                None
                if tolerance is None
                else round(tolerance)
            ),
            data_confidence_score=round(
                self._clamp(confidence)
            ),
            alerts=alerts,
            explanations=explanations,
        )

    @staticmethod
    def _status(score: int) -> str:
        if score < 35:
            return "RECUPERATION"
        if score < 55:
            return "ADAPTER"
        if score < 75:
            return "DISPONIBLE"
        return "OPTIMAL"

    @staticmethod
    def _clamp(
        value: float,
        minimum: float = 0.0,
        maximum: float = 100.0,
    ) -> float:
        return max(
            minimum,
            min(maximum, float(value)),
        )