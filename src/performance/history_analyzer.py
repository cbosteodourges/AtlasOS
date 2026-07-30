"""
ATLAS OS
Analyse de l’historique d’entraînement.
"""

from collections import defaultdict
from datetime import timedelta
from statistics import mean
from typing import Dict, List

from src.performance.models import (
    HistoryAnalysis,
    TrainingActivity,
)


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — ANALYSEUR
# ████████████████████████████████████████████████████████████

class TrainingHistoryAnalyzer:
    def analyse(
        self,
        activities: List[TrainingActivity],
    ) -> HistoryAnalysis:
        if not activities:
            return HistoryAnalysis(
                activity_count=0,
                total_distance_km=0,
                average_weekly_distance_km=0,
                maximum_weekly_distance_km=0,
                average_sessions_per_week=0,
                longest_activity_km=0,
                average_rpe=None,
                warnings=[
                    "Aucune activité historique disponible."
                ],
                data_quality_score=0,
            )

        ordered = sorted(
            activities,
            key=lambda activity: activity.activity_date,
        )

        weekly_activities = self._group_by_week(
            ordered
        )

        weekly_distances = [
            sum(
                activity.distance_km
                for activity in week
            )
            for week in weekly_activities.values()
        ]

        rpe_values = [
            activity.perceived_exertion
            for activity in ordered
            if activity.perceived_exertion is not None
        ]

        analysis = HistoryAnalysis(
            activity_count=len(ordered),
            total_distance_km=round(
                sum(
                    activity.distance_km
                    for activity in ordered
                ),
                1,
            ),
            average_weekly_distance_km=round(
                mean(weekly_distances),
                1,
            ),
            maximum_weekly_distance_km=round(
                max(weekly_distances),
                1,
            ),
            average_sessions_per_week=round(
                len(ordered)
                / len(weekly_activities),
                1,
            ),
            longest_activity_km=round(
                max(
                    activity.distance_km
                    for activity in ordered
                ),
                1,
            ),
            average_rpe=(
                round(mean(rpe_values), 1)
                if rpe_values
                else None
            ),
            data_quality_score=self._calculate_quality(
                ordered
            ),
        )

        self._detect_strengths(
            analysis,
            weekly_distances,
        )

        self._detect_warnings(
            analysis,
            weekly_distances,
        )

        self._build_hypotheses(
            analysis,
            ordered,
        )

        return analysis

    def _group_by_week(
        self,
        activities: List[TrainingActivity],
    ) -> Dict[str, List[TrainingActivity]]:
        grouped = defaultdict(list)

        for activity in activities:
            iso_year, iso_week, _ = (
                activity.activity_date.isocalendar()
            )

            key = f"{iso_year}-{iso_week:02d}"
            grouped[key].append(activity)

        return dict(grouped)

    def _calculate_quality(
        self,
        activities: List[TrainingActivity],
    ) -> int:
        score = 40

        if len(activities) >= 10:
            score += 15

        if len(activities) >= 30:
            score += 15

        if any(
            activity.average_heart_rate
            for activity in activities
        ):
            score += 10

        if any(
            activity.perceived_exertion
            is not None
            for activity in activities
        ):
            score += 10

        if all(
            activity.duration_minutes > 0
            for activity in activities
        ):
            score += 10

        return min(score, 100)

    def _detect_strengths(
        self,
        analysis: HistoryAnalysis,
        weekly_distances: List[float],
    ) -> None:
        if analysis.average_sessions_per_week >= 4:
            analysis.strengths.append(
                "Bonne régularité hebdomadaire."
            )

        if (
            analysis.longest_activity_km
            >= analysis.average_weekly_distance_km
            * 0.25
        ):
            analysis.strengths.append(
                "Présence régulière d’un travail d’endurance longue."
            )

        if len(weekly_distances) >= 4:
            recent = weekly_distances[-4:]

            if recent[-1] >= recent[0]:
                analysis.strengths.append(
                    "Progression récente du volume observée."
                )

    def _detect_warnings(
        self,
        analysis: HistoryAnalysis,
        weekly_distances: List[float],
    ) -> None:
        for index in range(
            1,
            len(weekly_distances),
        ):
            previous = weekly_distances[index - 1]
            current = weekly_distances[index]

            if previous <= 0:
                continue

            increase = (
                (current - previous)
                / previous
                * 100
            )

            if increase > 20:
                analysis.warnings.append(
                    "Au moins une hausse hebdomadaire "
                    "du volume supérieure à 20 % a été détectée."
                )
                break

        if analysis.average_sessions_per_week < 3:
            analysis.warnings.append(
                "Fréquence d’entraînement limitée "
                "pour préparer un objectif d’endurance."
            )

        if analysis.data_quality_score < 60:
            analysis.warnings.append(
                "La qualité des données historiques "
                "est encore insuffisante pour conclure fortement."
            )

    def _build_hypotheses(
        self,
        analysis: HistoryAnalysis,
        activities: List[TrainingActivity],
    ) -> None:
        completed = [
            activity
            for activity in activities
            if activity.completed
        ]

        interrupted = [
            activity
            for activity in activities
            if not activity.completed
        ]

        if interrupted:
            analysis.hypotheses.append(
                "Certaines séances n’ont pas été terminées. "
                "Le contexte, le sommeil, la douleur et le ressenti "
                "devront être étudiés."
            )

        high_rpe = [
            activity
            for activity in completed
            if (
                activity.perceived_exertion
                is not None
                and activity.perceived_exertion >= 8
            )
        ]

        if high_rpe:
            analysis.hypotheses.append(
                "Plusieurs séances présentent un effort perçu élevé. "
                "Atlas devra vérifier leur récupération à 24–48 heures."
            )

        if not analysis.hypotheses:
            analysis.hypotheses.append(
                "L’historique semble cohérent, mais davantage "
                "de ressenti utilisateur est nécessaire "
                "pour identifier les facteurs de réussite."
            )


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — AFFICHAGE
# ████████████████████████████████████████████████████████████

def display_history_analysis(
    analysis: HistoryAnalysis,
) -> None:
    print("=" * 60)
    print("ANALYSE DE L’HISTORIQUE")
    print("=" * 60)

    print(
        f"Activités analysées : "
        f"{analysis.activity_count}"
    )

    print(
        f"Distance totale : "
        f"{analysis.total_distance_km} km"
    )

    print(
        f"Volume hebdomadaire moyen : "
        f"{analysis.average_weekly_distance_km} km"
    )

    print(
        f"Volume hebdomadaire maximal : "
        f"{analysis.maximum_weekly_distance_km} km"
    )

    print(
        f"Séances par semaine : "
        f"{analysis.average_sessions_per_week}"
    )

    print(
        f"Sortie la plus longue : "
        f"{analysis.longest_activity_km} km"
    )

    print(
        f"RPE moyen : "
        f"{analysis.average_rpe or 'non disponible'}"
    )

    print(
        f"Qualité des données : "
        f"{analysis.data_quality_score}/100"
    )

    print()
    print("POINTS FAVORABLES")

    for strength in analysis.strengths:
        print(f"  + {strength}")

    if not analysis.strengths:
        print("  Aucun point fort confirmé.")

    print()
    print("POINTS DE VIGILANCE")

    for warning in analysis.warnings:
        print(f"  ! {warning}")

    if not analysis.warnings:
        print("  Aucun signal majeur détecté.")

    print()
    print("HYPOTHÈSES À CONFIRMER")

    for hypothesis in analysis.hypotheses:
        print(f"  ? {hypothesis}")

    print("=" * 60)


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████