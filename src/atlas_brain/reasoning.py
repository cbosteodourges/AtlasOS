"""
ATLAS OS
Moteur de raisonnement explicable.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

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

    Les scores du Physiology Engine sont utilisés en priorité lorsqu'ils sont
    disponibles. Le moteur conserve un calcul de secours pour les anciens
    profils qui ne possèdent pas encore de données physiologiques.

    Ce moteur ne pose pas de diagnostic médical.
    """

    def analyse(self, twin: "DigitalTwin") -> ReasoningResult:
        observations: List[str] = []
        favorable_factors: List[str] = []
        limiting_factors: List[str] = []
        uncertainties: List[str] = []

        physiology_recovery = self._number(
            twin.get_metric("physiology_recovery_score")
        )
        physiology_readiness = self._number(
            twin.get_metric("physiology_readiness_score")
        )
        physiology_sleep = self._number(
            twin.get_metric("physiology_sleep_score")
        )
        physiology_fatigue = self._number(
            twin.get_metric("physiology_fatigue_score")
        )

        physiology_available = (
            physiology_recovery is not None
            and physiology_readiness is not None
        )

        if physiology_available:
            recovery_score = round(physiology_recovery)
            readiness_score = round(physiology_readiness)
            observations.append(
                "Les scores de récupération et de disponibilité proviennent "
                "du moteur physiologique ATLAS."
            )
            observations.append(
                f"Récupération physiologique : {recovery_score}/100."
            )
            observations.append(
                f"Disponibilité physiologique : {readiness_score}/100."
            )

            if recovery_score >= 70:
                favorable_factors.append(
                    "La récupération physiologique du jour est favorable."
                )
            elif recovery_score < 55:
                limiting_factors.append(
                    "La récupération physiologique du jour est limitée."
                )

            if physiology_sleep is not None:
                observations.append(
                    f"Score de sommeil : {physiology_sleep:.0f}/100."
                )
                if physiology_sleep >= 75:
                    favorable_factors.append(
                        "Le sommeil contribue favorablement à la récupération."
                    )
                elif physiology_sleep < 55:
                    limiting_factors.append(
                        "Le sommeil limite la disponibilité du jour."
                    )

            if physiology_fatigue is not None:
                observations.append(
                    f"Fatigue physiologique estimée : "
                    f"{physiology_fatigue:.0f}/100."
                )
                if physiology_fatigue >= 60:
                    limiting_factors.append(
                        "Le niveau de fatigue physiologique est élevé."
                    )
        else:
            recovery_score = 70
            readiness_score = 70
            uncertainties.append(
                "Les résultats du moteur physiologique ne sont pas encore "
                "présents dans le jumeau numérique."
            )

        mechanical_risk_score = 10

        hrv = twin.get_metric("hrv")
        vo2max = twin.get_metric("vo2max")
        resting_hr = twin.get_metric("heart_rate")
        vma = twin.get_metric("vma_kmh")

        # --------------------------------------------------------
        # Données physiologiques générales
        # --------------------------------------------------------

        if hrv is not None:
            observations.append(f"VFC disponible : {hrv:.0f} ms.")
            favorable_factors.append(
                "La VFC peut être intégrée au suivi longitudinal."
            )
        else:
            if not physiology_available:
                recovery_score -= 10
            uncertainties.append("Aucune donnée de VFC disponible.")

        if resting_hr is not None:
            observations.append(
                f"Fréquence cardiaque enregistrée : {resting_hr:.0f} bpm."
            )
        else:
            uncertainties.append(
                "Fréquence cardiaque de repos indisponible."
            )

        if vo2max is not None:
            observations.append(f"VO₂max enregistrée : {vo2max:.1f}.")
        else:
            if not physiology_available:
                readiness_score -= 5
            uncertainties.append("VO₂max indisponible.")

        if vma is not None:
            observations.append(f"VMA enregistrée : {vma:.1f} km/h.")
        else:
            uncertainties.append("VMA indisponible ou non estimée.")

        # --------------------------------------------------------
        # Historique d'entraînement
        # --------------------------------------------------------

        analysis = twin.history_analysis

        if analysis is not None:
            observations.append(
                f"{analysis.activity_count} activités ont été analysées."
            )
            observations.append(
                "Volume hebdomadaire moyen observé : "
                f"{analysis.average_weekly_distance_km} km."
            )

            if analysis.average_sessions_per_week >= 3:
                favorable_factors.append(
                    "Régularité d'entraînement suffisante pour construire "
                    "un plan progressif."
                )
            else:
                if not physiology_available:
                    readiness_score -= 10
                limiting_factors.append(
                    "La fréquence d'entraînement historique est "
                    "relativement faible."
                )

            if analysis.warnings:
                mechanical_risk_score += min(
                    25,
                    len(analysis.warnings) * 8,
                )
                limiting_factors.extend(analysis.warnings)

            favorable_factors.extend(analysis.strengths)
            uncertainties.extend(analysis.hypotheses)
        else:
            if not physiology_available:
                readiness_score -= 15
            uncertainties.append("Aucun historique d'entraînement analysé.")

        # --------------------------------------------------------
        # Douleurs déclarées
        # --------------------------------------------------------

        active_pains = [
            pain for pain in twin.pain_records if pain.intensity > 0
        ]

        if active_pains:
            maximum_pain = max(pain.intensity for pain in active_pains)
            mechanical_risk_score += maximum_pain * 5

            # La douleur est déjà intégrée au Physiology Engine. Cette
            # pénalité n'est appliquée qu'au calcul de secours afin d'éviter
            # de compter deux fois le même facteur.
            if not physiology_available:
                readiness_score -= maximum_pain * 3

            limiting_factors.append(
                f"{len(active_pains)} douleur(s) actuellement enregistrée(s)."
            )

            for pain in active_pains:
                observations.append(
                    "Douleur : "
                    f"{pain.anatomical_structure_id}, "
                    f"intensité {pain.intensity}/10."
                )
        else:
            favorable_factors.append("Aucune douleur active enregistrée.")

        # --------------------------------------------------------
        # Plan actuel
        # --------------------------------------------------------

        if twin.training_plan is not None:
            observations.append(
                f"{twin.training_plan.total_workouts} séances sont "
                "actuellement planifiées."
            )
        else:
            if not physiology_available:
                readiness_score -= 5
            uncertainties.append("Aucun plan d'entraînement connecté.")

        # --------------------------------------------------------
        # Confiance dans les données
        # --------------------------------------------------------

        profile_completion = twin.get_profile_completion()
        history_quality = (
            analysis.data_quality_score if analysis is not None else 0
        )

        data_confidence_score = round(
            profile_completion * 0.6 + history_quality * 0.4
        )

        if data_confidence_score < 60:
            uncertainties.append(
                "Le niveau de confiance reste limité par des données "
                "incomplètes."
            )

        recovery_score = self._clamp(recovery_score)
        mechanical_risk_score = self._clamp(mechanical_risk_score)

        # Lorsque le moteur physiologique est disponible, sa disponibilité
        # devient la référence commune. Le risque mécanique reste affiché
        # séparément et guide les alertes et recommandations.
        if not physiology_available:
            readiness_score -= round(mechanical_risk_score * 0.25)

        readiness_score = self._clamp(readiness_score)

        return ReasoningResult(
            recovery_score=recovery_score,
            readiness_score=readiness_score,
            mechanical_risk_score=mechanical_risk_score,
            data_confidence_score=data_confidence_score,
            observations=self._unique(observations),
            favorable_factors=self._unique(favorable_factors),
            limiting_factors=self._unique(limiting_factors),
            uncertainties=self._unique(uncertainties),
        )

    @staticmethod
    def _number(value: object) -> Optional[float]:
        """Convertit une mesure du jumeau en nombre lorsqu'elle est valide."""
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
        return max(minimum, min(maximum, round(value)))

    @staticmethod
    def _unique(values: List[str]) -> List[str]:
        return list(dict.fromkeys(values))


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████
