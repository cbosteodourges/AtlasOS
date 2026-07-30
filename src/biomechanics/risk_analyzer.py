"""
ATLAS OS
Analyse indicative des risques biomécaniques.
"""

from dataclasses import dataclass, field
from typing import Any, List


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — RÉSULTAT DE RISQUE
# ████████████████████████████████████████████████████████████

@dataclass
class BiomechanicalRiskResult:
    score: int
    level: str
    factors: List[str] = field(default_factory=list)
    protective_factors: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — ANALYSEUR
# ████████████████████████████████████████████████████████████

class BiomechanicalRiskAnalyzer:
    def analyse(
        self,
        pain: Any,
        history_analysis: Any = None,
    ) -> BiomechanicalRiskResult:
        score = 10
        factors: List[str] = []
        protective_factors: List[str] = []
        uncertainties: List[str] = []

        intensity = self._safe_number(
            getattr(pain, "intensity", 0)
        )

        if intensity >= 7:
            score += 55
            factors.append(
                "Douleur d'intensité élevée."
            )
        elif intensity >= 4:
            score += 35
            factors.append(
                "Douleur d'intensité modérée."
            )
        elif intensity > 0:
            score += 15
            factors.append(
                "Douleur légère actuellement enregistrée."
            )

        if history_analysis is not None:
            warnings = list(
                getattr(
                    history_analysis,
                    "warnings",
                    [],
                )
                or []
            )

            strengths = list(
                getattr(
                    history_analysis,
                    "strengths",
                    [],
                )
                or []
            )

            score += min(30, len(warnings) * 8)
            factors.extend(warnings)
            protective_factors.extend(strengths)

            activity_count = self._safe_number(
                getattr(
                    history_analysis,
                    "activity_count",
                    0,
                )
            )

            if activity_count >= 8:
                protective_factors.append(
                    "Historique suffisant pour observer "
                    "la régularité de l'entraînement."
                )
            else:
                score += 5
                uncertainties.append(
                    "Historique d'activité encore limité."
                )
        else:
            score += 10
            uncertainties.append(
                "Aucune analyse de l'historique disponible."
            )

        score = max(0, min(100, round(score)))

        if score >= 70:
            level = "élevé"
        elif score >= 40:
            level = "modéré"
        else:
            level = "faible"

        return BiomechanicalRiskResult(
            score=score,
            level=level,
            factors=self._unique(factors),
            protective_factors=self._unique(
                protective_factors
            ),
            uncertainties=self._unique(
                uncertainties
            ),
        )

    @staticmethod
    def _safe_number(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _unique(values: List[str]) -> List[str]:
        return list(dict.fromkeys(values))


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████