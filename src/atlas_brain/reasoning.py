"""
ATLAS OS
Moteur de raisonnement explicable.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from src.twin import DigitalTwin


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — RÉSULTAT DU RAISONNEMENT
# ████████████████████████████████████████████████████████████

@dataclass
class ReasoningResult:
    recovery_score: int
    readiness_score: int
    mechanical_risk_score: int
    data_confidence_score: int

    observations: List[str] = field(default_factory=list)
    favorable_factors: List[str] = field(default_factory=list)
    limiting_factors: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — MOTEUR DE RAISONNEMENT
# ████████████████████████████████████████████████████████████

class AtlasReasoningEngine:
    """
    Analyse les informations présentes dans le Digital Twin.

    Ce moteur ne pose pas de diagnostic médical.
    Il produit des observations, des scores indicatifs
    et des éléments utiles à la personnalisation.
    """

    def analyse(
        self,
        twin: "DigitalTwin",
    ) -> ReasoningResult:
        recovery_score = 70
        readiness_score = 70
        mechanical_risk_score = 10

        observations: List[str] = []
        favorable_factors: List[str] = []
        limiting_factors: List[str] = []
        uncertainties: List[str] = []

        hrv = twin.get_metric("hrv")
        vo2max = twin.get_metric("vo2max")
        resting_hr = twin.get_metric("heart_rate")
        vma = twin.get_metric("vma_kmh")

        # --------------------------------------------------------
        # Données physiologiques disponibles
        # --------------------------------------------------------

        if hrv is not None:
            observations.append(
                f"VFC disponible : {hrv:.0f} ms."
            )
            favorable_factors.append(
                "La VFC peut être intégrée au suivi longitudinal."
            )
        else:
            recovery_score -= 10
            uncertainties.append(
                "Aucune donnée de VFC disponible."
            )

        if resting_hr is not None:
            observations.append(
                f"Fréquence cardiaque enregistrée : "
                f"{resting_hr:.0f} bpm."
            )
        else:
            uncertainties.append(
                "Fréquence cardiaque de repos indisponible."
            )

        if vo2max is not None:
            observations.append(
                f"VO₂max enregistrée : {vo2max:.1f}."
            )
        else:
            readiness_score -= 5
            uncertainties.append(
                "VO₂max indisponible."
            )

        if vma is not None:
            observations.append(
                f"VMA enregistrée : {vma:.1f} km/h."
            )
        else:
            uncertainties.append(
                "VMA indisponible ou non estimée."
            )

        # --------------------------------------------------------
        # Historique d'entraînement
        # --------------------------------------------------------

        analysis = twin.history_analysis

        if analysis is not None:
            observations.append(
                f"{analysis.activity_count} activités "
                f"ont été analysées."
            )

            observations.append(
                "Volume hebdomadaire moyen observé : "
                f"{analysis.average_weekly_distance_km} km."
            )

            if analysis.average_sessions_per_week >= 3:
                favorable_factors.append(
                    "Régularité d'entraînement suffisante "
                    "pour construire un plan progressif."
                )
            else:
                readiness_score -= 10
                limiting_factors.append(
                    "La fréquence d'entraînement historique "
                    "est relativement faible."
                )

            if analysis.warnings:
                mechanical_risk_score += min(
                    25,
                    len(analysis.warnings) * 8,
                )

                limiting_factors.extend(
                    analysis.warnings
                )

            favorable_factors.extend(
                analysis.strengths
            )

            uncertainties.extend(
                analysis.hypotheses
            )
        else:
            readiness_score -= 15
            uncertainties.append(
                "Aucun historique d'entraînement analysé."
            )

        # --------------------------------------------------------
        # Douleurs déclarées
        # --------------------------------------------------------

        active_pains = [
            pain
            for pain in twin.pain_records
            if pain.intensity > 0
        ]

        if active_pains:
            maximum_pain = max(
                pain.intensity
                for pain in active_pains
            )

            mechanical_risk_score += (
                maximum_pain * 5
            )

            readiness_score -= (
                maximum_pain * 3
            )

            limiting_factors.append(
                f"{len(active_pains)} douleur(s) "
                f"actuellement enregistrée(s)."
            )

            for pain in active_pains:
                observations.append(
                    "Douleur : "
                    f"{pain.anatomical_structure_id}, "
                    f"intensité {pain.intensity}/10."
                )
        else:
            favorable_factors.append(
                "Aucune douleur active enregistrée."
            )

        # --------------------------------------------------------
        # Plan actuel
        # --------------------------------------------------------

        if twin.training_plan is not None:
            observations.append(
                f"{twin.training_plan.total_workouts} séances "
                "sont actuellement planifiées."
            )
        else:
            readiness_score -= 5
            uncertainties.append(
                "Aucun plan d'entraînement connecté."
            )

        # --------------------------------------------------------
        # Confiance dans les données
        # --------------------------------------------------------

        profile_completion = (
            twin.get_profile_completion()
        )

        history_quality = (
            analysis.data_quality_score
            if analysis is not None
            else 0
        )

        data_confidence_score = round(
            profile_completion * 0.6
            + history_quality * 0.4
        )

        if data_confidence_score < 60:
            uncertainties.append(
                "Le niveau de confiance reste limité "
                "par des données incomplètes."
            )

        recovery_score = self._clamp(
            recovery_score,
        )

        mechanical_risk_score = self._clamp(
            mechanical_risk_score,
        )

        readiness_score -= round(
            mechanical_risk_score * 0.25
        )

        readiness_score = self._clamp(
            readiness_score,
        )

        return ReasoningResult(
            recovery_score=recovery_score,
            readiness_score=readiness_score,
            mechanical_risk_score=mechanical_risk_score,
            data_confidence_score=data_confidence_score,
            observations=self._unique(observations),
            favorable_factors=self._unique(
                favorable_factors
            ),
            limiting_factors=self._unique(
                limiting_factors
            ),
            uncertainties=self._unique(
                uncertainties
            ),
        )

    @staticmethod
    def _clamp(
        value: int,
        minimum: int = 0,
        maximum: int = 100,
    ) -> int:
        return max(
            minimum,
            min(maximum, round(value)),
        )

    @staticmethod
    def _unique(
        values: List[str],
    ) -> List[str]:
        return list(dict.fromkeys(values))


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████