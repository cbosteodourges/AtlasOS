"""
ATLAS OS
Moteur d'explication grand public.
"""

from typing import List

from src.atlas_brain.alerts import AtlasAlert
from src.atlas_brain.diagnosis import AtlasHypothesis
from src.atlas_brain.reasoning import ReasoningResult
from src.atlas_brain.recommendations import (
    AtlasRecommendation,
)


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — EXPLICATION
# ████████████████████████████████████████████████████████████

class AtlasExplanationEngine:
    def build_summary(
        self,
        first_name: str,
        reasoning: ReasoningResult,
        hypotheses: List[AtlasHypothesis],
        alerts: List[AtlasAlert],
        recommendations: List[
            AtlasRecommendation
        ],
    ) -> str:
        if reasoning.readiness_score >= 75:
            state = "ton état général paraît favorable"
        elif reasoning.readiness_score >= 50:
            state = (
                "ton état général paraît intermédiaire"
            )
        else:
            state = (
                "ton état général nécessite davantage "
                "de prudence"
            )

        main_recommendation = (
            recommendations[0].title
            if recommendations
            else "poursuivre l'observation"
        )

        main_hypothesis = (
            hypotheses[0].title
            if hypotheses
            else "aucune hypothèse dominante"
        )

        alert_text = (
            f"{len(alerts)} alerte(s) ont été détectée(s)"
            if alerts
            else "aucune alerte majeure n'a été détectée"
        )

        return (
            f"Bonjour {first_name}. "
            f"D'après les informations actuellement disponibles, "
            f"{state}. "
            f"L'hypothèse principale est : "
            f"{main_hypothesis}. "
            f"{alert_text}. "
            f"La priorité proposée est : "
            f"{main_recommendation}. "
            f"Le niveau de confiance actuel est de "
            f"{reasoning.data_confidence_score} %."
        )

    def build_detailed_explanation(
        self,
        reasoning: ReasoningResult,
        recommendations: List[
            AtlasRecommendation
        ],
    ) -> List[str]:
        paragraphs: List[str] = []

        paragraphs.append(
            "Atlas a combiné les informations du profil, "
            "de l'historique, du plan d'entraînement "
            "et des douleurs enregistrées."
        )

        paragraphs.append(
            "Disponibilité estimée : "
            f"{reasoning.readiness_score}/100. "
            "Récupération estimée : "
            f"{reasoning.recovery_score}/100. "
            "Vigilance mécanique : "
            f"{reasoning.mechanical_risk_score}/100."
        )

        if reasoning.favorable_factors:
            paragraphs.append(
                "Éléments favorables : "
                + " ".join(
                    reasoning.favorable_factors
                )
            )

        if reasoning.limiting_factors:
            paragraphs.append(
                "Éléments limitants : "
                + " ".join(
                    reasoning.limiting_factors
                )
            )

        if recommendations:
            paragraphs.append(
                "La recommandation principale est : "
                f"{recommendations[0].description}"
            )

        paragraphs.append(
            "Ces résultats sont indicatifs et ne remplacent "
            "pas une évaluation par un professionnel de santé "
            "en cas de douleur importante, persistante ou "
            "de symptôme inhabituel."
        )

        return paragraphs


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████