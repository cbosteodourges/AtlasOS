"""
ATLAS OS
Moteur d'alertes.
"""

from dataclasses import dataclass
from typing import List

from src.atlas_brain.reasoning import ReasoningResult


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — ALERTE
# ████████████████████████████████████████████████████████████

@dataclass
class AtlasAlert:
    code: str
    level: str
    title: str
    message: str
    action_required: bool = False


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — MOTEUR D'ALERTES
# ████████████████████████████████████████████████████████████

class AtlasAlertEngine:
    def generate(
        self,
        reasoning: ReasoningResult,
    ) -> List[AtlasAlert]:
        alerts: List[AtlasAlert] = []

        if reasoning.mechanical_risk_score >= 70:
            alerts.append(
                AtlasAlert(
                    code="MECHANICAL_HIGH",
                    level="high",
                    title="Charge mécanique élevée",
                    message=(
                        "Une douleur importante ou plusieurs "
                        "facteurs de surcharge sont présents. "
                        "Une séance exigeante doit être évitée "
                        "jusqu'à réévaluation."
                    ),
                    action_required=True,
                )
            )

        elif reasoning.mechanical_risk_score >= 40:
            alerts.append(
                AtlasAlert(
                    code="MECHANICAL_MODERATE",
                    level="moderate",
                    title="Vigilance biomécanique",
                    message=(
                        "Une adaptation du volume ou de "
                        "l'intensité peut être pertinente."
                    ),
                )
            )

        if reasoning.recovery_score < 45:
            alerts.append(
                AtlasAlert(
                    code="RECOVERY_LOW",
                    level="moderate",
                    title="Récupération à surveiller",
                    message=(
                        "Les informations disponibles ne "
                        "permettent pas de confirmer une "
                        "récupération suffisante."
                    ),
                )
            )

        if reasoning.readiness_score < 40:
            alerts.append(
                AtlasAlert(
                    code="READINESS_LOW",
                    level="high",
                    title="Disponibilité réduite",
                    message=(
                        "Le contexte actuel paraît peu favorable "
                        "à une séance difficile."
                    ),
                    action_required=True,
                )
            )

        if reasoning.data_confidence_score < 50:
            alerts.append(
                AtlasAlert(
                    code="DATA_LOW",
                    level="information",
                    title="Données insuffisantes",
                    message=(
                        "Atlas manque encore d'informations "
                        "pour personnaliser fortement "
                        "ses recommandations."
                    ),
                )
            )

        return alerts


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████