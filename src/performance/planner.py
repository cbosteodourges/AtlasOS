"""
ATLAS OS
Premier générateur de plans d’entraînement.
"""

from datetime import date, timedelta
from typing import List

from src.performance.models import (
    HistoryAnalysis,
    PerformanceGoal,
    PlannedWorkout,
    TrainingPlan,
    TrainingWeek,
)


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — GÉNÉRATEUR
# ████████████████████████████████████████████████████████████

class RunningPlanGenerator:
    def generate(
        self,
        goal: PerformanceGoal,
        analysis: HistoryAnalysis,
        weeks_count: int = 4,
    ) -> TrainingPlan:
        today = date.today()

        days_until_event = (
            goal.event_date - today
        ).days

        if days_until_event <= 0:
            raise ValueError(
                "La date de l’objectif doit être future."
            )

        maximum_weeks = max(
            1,
            days_until_event // 7,
        )

        weeks_count = min(
            weeks_count,
            maximum_weeks,
        )

        plan = TrainingPlan(
            goal=goal,
            created_at=today,
            explanation=self._build_explanation(
                goal,
                analysis,
            ),
        )

        base_duration = self._calculate_base_duration(
            analysis
        )

        for week_index in range(weeks_count):
            start_date = (
                today
                + timedelta(
                    days=week_index * 7
                )
            )

            end_date = (
                start_date
                + timedelta(days=6)
            )

            is_recovery_week = (
                week_index == 3
            )

            progression_factor = (
                0.85
                if is_recovery_week
                else 1 + week_index * 0.05
            )

            week = TrainingWeek(
                week_number=week_index + 1,
                start_date=start_date,
                end_date=end_date,
                objective=(
                    "Assimilation et récupération"
                    if is_recovery_week
                    else "Développement progressif"
                ),
            )

            week.workouts = self._build_week(
                start_date=start_date,
                base_duration=base_duration,
                progression_factor=progression_factor,
                include_intensity=(
                    not is_recovery_week
                ),
            )

            plan.weeks.append(week)

        return plan

    def _calculate_base_duration(
        self,
        analysis: HistoryAnalysis,
    ) -> int:
        if analysis.average_weekly_distance_km >= 50:
            return 55

        if analysis.average_weekly_distance_km >= 30:
            return 45

        return 35

    def _build_week(
        self,
        start_date: date,
        base_duration: int,
        progression_factor: float,
        include_intensity: bool,
    ) -> List[PlannedWorkout]:
        easy_duration = round(
            base_duration
            * progression_factor
        )

        long_duration = round(
            base_duration
            * 1.45
            * progression_factor
        )

        workouts = [
            PlannedWorkout(
                workout_date=(
                    start_date
                    + timedelta(days=1)
                ),
                title="Endurance fondamentale",
                description=(
                    "Course confortable et régulière."
                ),
                duration_minutes=easy_duration,
                zone_number=2,
                objective=(
                    "Développer la base aérobie "
                    "avec une fatigue limitée."
                ),
                intensity_description=(
                    "Z2 : 60–70 % FCmax "
                    "et 65–75 % VMA."
                ),
                recovery_description=(
                    "Récupération normale attendue "
                    "dans les 24 heures."
                ),
            ),
            PlannedWorkout(
                workout_date=(
                    start_date
                    + timedelta(days=3)
                ),
                title=(
                    "Travail au seuil"
                    if include_intensity
                    else "Endurance légère"
                ),
                description=(
                    "3 × 8 minutes en zone 4 "
                    "avec 3 minutes de récupération."
                    if include_intensity
                    else
                    "Séance facile sans travail intense."
                ),
                duration_minutes=(
                    round(
                        base_duration
                        * 1.1
                    )
                    if include_intensity
                    else easy_duration
                ),
                zone_number=(
                    4
                    if include_intensity
                    else 2
                ),
                objective=(
                    "Améliorer la capacité à maintenir "
                    "une intensité soutenue."
                    if include_intensity
                    else
                    "Favoriser l’assimilation de la charge."
                ),
                intensity_description=(
                    "Blocs en Z4 : 80–90 % FCmax "
                    "et 85–95 % VMA."
                    if include_intensity
                    else
                    "Z1–Z2 uniquement."
                ),
                recovery_description=(
                    "Prévoir environ 48 heures "
                    "avant une autre séance exigeante."
                    if include_intensity
                    else
                    "Récupération rapide attendue."
                ),
            ),
            PlannedWorkout(
                workout_date=(
                    start_date
                    + timedelta(days=5)
                ),
                title="Sortie longue progressive",
                description=(
                    "Début en zone 2, "
                    "fin contrôlée en zone 3."
                ),
                duration_minutes=long_duration,
                zone_number=2,
                objective=(
                    "Développer l’endurance "
                    "et la tolérance au volume."
                ),
                intensity_description=(
                    "Environ 75 % de la séance en Z2 "
                    "puis 25 % en Z3."
                ),
                recovery_description=(
                    "Le lendemain doit rester facile "
                    "ou consacré au repos."
                ),
            ),
        ]

        return workouts

    def _build_explanation(
        self,
        goal: PerformanceGoal,
        analysis: HistoryAnalysis,
    ) -> str:
        return (
            f"Le plan prépare l’objectif « {goal.name} ». "
            f"Il s’appuie sur un volume hebdomadaire historique "
            f"moyen de {analysis.average_weekly_distance_km} km "
            f"et sur {analysis.average_sessions_per_week} séances "
            f"par semaine. La progression reste volontairement "
            f"prudente et privilégie le volume facile avant "
            f"d’augmenter l’intensité."
        )


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — AFFICHAGE DU PLAN
# ████████████████████████████████████████████████████████████

def display_training_plan(
    plan: TrainingPlan,
) -> None:
    print("=" * 60)
    print("PLAN D’ENTRAÎNEMENT ATLAS")
    print("=" * 60)

    print(f"Objectif : {plan.goal.name}")
    print(f"Date : {plan.goal.event_date}")
    print(f"Distance : {plan.goal.distance_km} km")
    print(f"Séances : {plan.total_workouts}")

    print()
    print("POURQUOI CE PLAN ?")
    print(plan.explanation)

    for week in plan.weeks:
        print()
        print("-" * 60)
        print(
            f"SEMAINE {week.week_number} "
            f"— {week.start_date} au {week.end_date}"
        )
        print(f"Objectif : {week.objective}")
        print(
            f"Durée totale : "
            f"{week.total_duration_minutes} minutes"
        )

        for workout in week.workouts:
            print()
            print(
                f"{workout.workout_date} "
                f"— {workout.title}"
            )

            print(
                f"Durée : "
                f"{workout.duration_minutes} minutes"
            )

            print(
                f"Zone principale : "
                f"Z{workout.zone_number}"
            )

            print(workout.description)
            print(
                f"Objectif : {workout.objective}"
            )

            print(
                f"Intensité : "
                f"{workout.intensity_description}"
            )

            print(
                f"Récupération : "
                f"{workout.recovery_description}"
            )

    print()
    print("=" * 60)


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████