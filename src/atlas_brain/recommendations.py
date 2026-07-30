"""
ATLAS OS
Moteur de recommandations.
"""

from dataclasses import dataclass
from typing import List

from src.atlas_brain.alerts import AtlasAlert
from src.atlas_brain.reasoning import ReasoningResult


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — RECOMMANDATION
# ████████████████████████████████████████████████████████████

@dataclass
class AtlasRecommendation:
    priority: int
    category: str
    title: str
    description: str
    reason: str
    confidence: int


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — MOTEUR DE RECOMMANDATIONS
# ████████████████████████████████████████████████████████████

class AtlasRecommendationEngine:
    def generate(
        self,
        reasoning: ReasoningResult,
        alerts: List[AtlasAlert],
    ) -> List[AtlasRecommendation]:
        recommendations: List[
            AtlasRecommendation
        ] = []

        high_alert = any(
            alert.level == "high"
            for alert in alerts
        )

        if high_alert:
            recommendations.append(
                AtlasRecommendation(
                    priority=1,
                    category="entraînement",
                    title=(
                        "Réduire la charge aujourd'hui"
                    ),
                    description=(
                        "Remplacer la séance intense par "
                        "une récupération active, une marche "
                        "ou une courte séance facile."
                    ),
                    reason=(
                        "Un signal de vigilance élevé "
                        "a été identifié."
                    ),
                    confidence=(
                        reasoning.data_confidence_score
                    ),
                )
            )

        elif reasoning.mechanical_risk_score >= 40:
            recommendations.append(
                AtlasRecommendation(
                    priority=1,
                    category="entraînement",
                    title=(
                        "Privilégier une séance facile"
                    ),
                    description=(
                        "Réaliser une séance en zone 1 ou 2 "
                        "sans accélération importante."
                    ),
                    reason=(
                        "La tolérance mécanique paraît "
                        "moins favorable qu'habituellement."
                    ),
                    confidence=(
                        reasoning.data_confidence_score
                    ),
                )
            )

        elif reasoning.readiness_score >= 75:
            recommendations.append(
                AtlasRecommendation(
                    priority=1,
                    category="performance",
                    title=(
                        "Maintenir la séance prévue"
                    ),
                    description=(
                        "Les données disponibles sont "
                        "compatibles avec la poursuite "
                        "du plan actuel."
                    ),
                    reason=(
                        "La disponibilité globale est favorable."
                    ),
                    confidence=(
                        reasoning.data_confidence_score
                    ),
                )
            )

        else:
            recommendations.append(
                AtlasRecommendation(
                    priority=1,
                    category="entraînement",
                    title=(
                        "Maintenir une charge modérée"
                    ),
                    description=(
                        "Privilégier une séance contrôlée "
                        "en endurance fondamentale."
                    ),
                    reason=(
                        "La situation est intermédiaire "
                        "et nécessite encore du suivi."
                    ),
                    confidence=(
                        reasoning.data_confidence_score
                    ),
                )
            )

        if reasoning.recovery_score < 60:
            recommendations.append(
                AtlasRecommendation(
                    priority=2,
                    category="récupération",
                    title=(
                        "Renforcer la récupération"
                    ),
                    description=(
                        "Accorder une attention particulière "
                        "au sommeil, à l'hydratation et "
                        "à la récupération entre les séances."
                    ),
                    reason=(
                        "Le score de récupération "
                        "est inférieur au niveau optimal."
                    ),
                    confidence=(
                        reasoning.data_confidence_score
                    ),
                )
            )

        if reasoning.data_confidence_score < 70:
            recommendations.append(
                AtlasRecommendation(
                    priority=3,
                    category="données",
                    title=(
                        "Compléter le suivi utilisateur"
                    ),
                    description=(
                        "Ajouter le sommeil, le ressenti, "
                        "la douleur, la VFC et la réponse "
                        "à 24 heures après les séances."
                    ),
                    reason=(
                        "De meilleures données permettront "
                        "une personnalisation plus fiable."
                    ),
                    confidence=100,
                )
            )

        return sorted(
            recommendations,
            key=lambda item: item.priority,
        )


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████