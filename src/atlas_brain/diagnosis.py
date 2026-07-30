"""
ATLAS OS
Moteur d'hypothèses et d'évaluation.

Le terme "diagnosis" correspond ici au nom technique historique
du module. Ce composant ne pose pas de diagnostic médical.
"""

from dataclasses import dataclass
from typing import List

from src.atlas_brain.reasoning import ReasoningResult


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — HYPOTHÈSE ATLAS
# ████████████████████████████████████████████████████████████

@dataclass
class AtlasHypothesis:
    title: str
    probability: int
    category: str
    explanation: str
    status: str = "à confirmer"


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — GÉNÉRATEUR D'HYPOTHÈSES
# ████████████████████████████████████████████████████████████

class AtlasHypothesisEngine:
    def generate(
        self,
        reasoning: ReasoningResult,
    ) -> List[AtlasHypothesis]:
        hypotheses: List[AtlasHypothesis] = []

        if reasoning.mechanical_risk_score >= 60:
            hypotheses.append(
                AtlasHypothesis(
                    title=(
                        "Tolérance mécanique réduite"
                    ),
                    probability=min(
                        90,
                        reasoning.mechanical_risk_score,
                    ),
                    category="biomécanique",
                    explanation=(
                        "La présence de douleurs ou de signaux "
                        "de charge suggère une prudence accrue."
                    ),
                )
            )

        elif reasoning.mechanical_risk_score >= 30:
            hypotheses.append(
                AtlasHypothesis(
                    title=(
                        "Vigilance mécanique nécessaire"
                    ),
                    probability=(
                        reasoning.mechanical_risk_score
                    ),
                    category="biomécanique",
                    explanation=(
                        "Certains facteurs peuvent réduire "
                        "la tolérance aux séances exigeantes."
                    ),
                )
            )

        if reasoning.recovery_score < 50:
            hypotheses.append(
                AtlasHypothesis(
                    title="Récupération possiblement incomplète",
                    probability=(
                        100 - reasoning.recovery_score
                    ),
                    category="physiologie",
                    explanation=(
                        "Les données actuellement disponibles "
                        "ne permettent pas de confirmer "
                        "une récupération optimale."
                    ),
                )
            )

        if reasoning.readiness_score >= 75:
            hypotheses.append(
                AtlasHypothesis(
                    title="Disponibilité favorable",
                    probability=(
                        reasoning.readiness_score
                    ),
                    category="performance",
                    explanation=(
                        "Les éléments disponibles sont "
                        "globalement compatibles avec "
                        "la réalisation du programme prévu."
                    ),
                    status="probable",
                )
            )

        if reasoning.data_confidence_score < 60:
            hypotheses.append(
                AtlasHypothesis(
                    title="Interprétation encore incertaine",
                    probability=(
                        100
                        - reasoning.data_confidence_score
                    ),
                    category="qualité_des_données",
                    explanation=(
                        "Des données supplémentaires sont "
                        "nécessaires avant de personnaliser "
                        "plus fortement les décisions."
                    ),
                )
            )

        if not hypotheses:
            hypotheses.append(
                AtlasHypothesis(
                    title="Situation globalement stable",
                    probability=60,
                    category="général",
                    explanation=(
                        "Aucun signal dominant n'est détecté, "
                        "mais le suivi longitudinal doit continuer."
                    ),
                )
            )

        return sorted(
            hypotheses,
            key=lambda item: item.probability,
            reverse=True,
        )


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████