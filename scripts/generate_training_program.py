"""Génère un programme Atlas Coach depuis l’historique réel."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_athlete_profile import (  # noqa: E402
    build_availability,
    build_physiological,
    load_activities,
    load_competitions,
    load_declared_profile,
    optional_float,
)
from src.performance import AthleteProfileBuilder  # noqa: E402
from src.performance.models import PerformanceGoal  # noqa: E402
from src.training.historical_workout_pattern_analyzer import (
    HistoricalWorkoutPatternAnalyzer,
)
from src.training.historical_workout_progression_selector import (
    HistoricalWorkoutProgressionSelector,
)
from src.training.competition_history_personalizer import (
    CompetitionHistoryPersonalizer,
)
from src.training.training_history_personalizer import (
    TrainingHistoryPersonalizer,
)
from src.training import (  # noqa: E402
    ProgramGenerationSettings,
    TrainingProgramGenerator,
    WorkoutType,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les paramètres de génération."""
    parser = argparse.ArgumentParser(
        description=(
            "Génère un programme Atlas Coach guidé "
            "par Atlas Research."
        )
    )
    parser.add_argument(
        "--activities",
        default="atlas-data/garmin/Activities.csv",
        help="Historique CSV Garmin.",
    )
    parser.add_argument(
        "--competitions",
        default=(
            "atlas-data/private/"
            "competition-events.json"
        ),
        help="Compétitions confirmées.",
    )
    parser.add_argument(
        "--profile-input",
        default=(
            "atlas-data/private/"
            "athlete-profile-input.json"
        ),
        help="Informations déclarées par l’utilisateur.",
    )
    parser.add_argument(
        "--training-history-fusion",
        default=(
            "atlas-data/private/"
            "training-history-fusion.json"
        ),
        help="Mémoire fusionnée FIT + Wellness.",
    )
    parser.add_argument(
        "--competition-comparison",
        default=(
            "atlas-data/private/"
            "garmin-competition-comparison.json"
        ),
        help="Comparaison des préparations passées.",
    )
    parser.add_argument(
        "--detailed-fit-history",
        default=(
            "atlas-data/private/"
            "marcq-2025-fit-analysis.json"
        ),
        help="Historique FIT détaillé pour apprendre les séances.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "training-program.json"
        ),
        help="Programme privé à générer.",
    )
    parser.add_argument(
        "--goal-name",
        required=True,
        help="Nom de la compétition cible.",
    )
    parser.add_argument(
        "--event-date",
        required=True,
        help="Date de compétition au format AAAA-MM-JJ.",
    )
    parser.add_argument(
        "--distance-km",
        required=True,
        type=float,
        help="Distance de l’objectif en kilomètres.",
    )
    parser.add_argument(
        "--target-time-minutes",
        type=int,
        help="Temps cible en minutes.",
    )
    parser.add_argument(
        "--start-date",
        default=date.today().isoformat(),
        help="Début du programme au format AAAA-MM-JJ.",
    )
    parser.add_argument(
        "--running-sessions",
        type=int,
        help="Nombre de séances de course par semaine.",
    )
    parser.add_argument(
        "--strength-sessions",
        type=int,
        default=2,
        help="Nombre de renforcements par semaine.",
    )
    parser.add_argument(
        "--preferred-long-run-day",
        default="sunday",
        choices=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        help="Jour préféré de sortie longue.",
    )
    parser.add_argument(
        "--recovery-status-available",
        action="store_true",
        help=(
            "Indique que l’état de récupération du jour "
            "est disponible."
        ),
    )
    return parser.parse_args()


def build_profile(arguments: argparse.Namespace):
    """Reconstruit le profil longitudinal réel."""
    declared = load_declared_profile(
        arguments.profile_input
    )
    activities = load_activities(
        arguments.activities
    )
    competitions = load_competitions(
        arguments.competitions
    )

    profile = AthleteProfileBuilder().build(
        athlete_id=str(declared["athlete_id"]),
        declared_level=str(
            declared["declared_level"]
        ),
        activities=activities,
        competitions=competitions,
        physiological=build_physiological(declared),
        availability=build_availability(declared),
        training_age_years=optional_float(
            declared.get("training_age_years")
        ),
    )
    profile.current_pain_or_injury = bool(
        declared.get("current_pain_or_injury", False)
    )
    profile.pain_or_injury_notes = str(
        declared.get("pain_or_injury_notes") or ""
    )
    profile.medical_constraints = list(
        declared.get("medical_constraints", [])
    )
    return profile


def apply_training_history(
    profile,
    input_path: str,
):
    """Applique la mémoire FIT + Wellness au profil."""
    source = Path(input_path)

    if not source.is_file():
        return None

    with source.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    if not isinstance(payload, dict):
        raise ValueError(
            "La mémoire FIT + Wellness doit être un objet JSON."
        )

    personalizer = TrainingHistoryPersonalizer()
    personalization = personalizer.build(payload)
    personalizer.apply(profile, personalization)
    return personalization

def build_competition_personalization(
    input_path: str,
    goal_distance_km: float,
):
    """Construit les préférences issues des compétitions comparables."""
    source = Path(input_path)
    if not source.is_file():
        return None

    with source.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    if not isinstance(payload, dict):
        raise ValueError(
            "La comparaison des compétitions doit être un objet JSON."
        )

    return CompetitionHistoryPersonalizer().build(
        payload,
        goal_distance_km=goal_distance_km,
    )


def build_historical_progression(
    fit_input_path: str,
    competition_input_path: str,
    profile,
    goal: PerformanceGoal,
):
    """Construit la progression depuis tous les FIT détaillés."""
    fit_source = Path(fit_input_path)
    competition_source = Path(competition_input_path)

    if not fit_source.is_file():
        return None

    with fit_source.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        fit_payload = json.load(input_file)

    competition_payload = None
    if competition_source.is_file():
        with competition_source.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            competition_payload = json.load(input_file)

    goal_speed_kmh = (
        round(
            goal.distance_km
            / (goal.target_time_minutes / 60),
            2,
        )
        if goal.target_time_minutes is not None
        else None
    )
    memory = HistoricalWorkoutPatternAnalyzer().analyze(
        fit_payload,
        vma_kmh=profile.physiological.vma_kmh,
        goal_speed_kmh=goal_speed_kmh,
        goal_distance_km=goal.distance_km,
        competition_payload=competition_payload,
    )
    progression = (
        HistoricalWorkoutProgressionSelector().build(
            memory.patterns
        )
    )
    return progression if progression.available else None

def build_settings(
    arguments: argparse.Namespace,
    profile,
    personalization=None,
    competition_personalization=None,
) -> ProgramGenerationSettings:
    """Combine les préférences CLI et le profil."""
    running_sessions = arguments.running_sessions

    if running_sessions is None:
        available_days = (
            profile.availability.available_days_per_week
            or 4
        )
        running_sessions = min(
            4,
            int(available_days),
        )

    running_sessions = max(
        2,
        min(7, int(running_sessions)),
    )

    cycling_sessions = (
        personalization.cycling_sessions_per_week
        if personalization is not None
        else 0
    )
    progression = (
        personalization.maximum_weekly_progression_percent
        if personalization is not None
        else 8.0
    )

    return ProgramGenerationSettings(
        running_sessions_per_week=running_sessions,
        optional_running_sessions_per_week=1,
        strength_sessions_per_week=(
            arguments.strength_sessions
        ),
        cycling_sessions_per_week=cycling_sessions,
        preferred_long_run_day=(
            arguments.preferred_long_run_day
        ),
        include_mobility=True,
        avoid_consecutive_intense_days=True,
        maximum_weekly_progression_percent=progression,
        prioritize_metabolic_quality=bool(
            competition_personalization is not None
            and competition_personalization
            .prioritize_metabolic_quality
        ),
        race_week_sharpening_days_before=(
            round(
                competition_personalization
                .target_days_since_last_intensity
            )
            if (
                competition_personalization is not None
                and competition_personalization
                .target_days_since_last_intensity
                is not None
            )
            else None
        ),
    )


def json_default(value: Any) -> Any:
    """Convertit les dates et énumérations en JSON."""
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value

    raise TypeError(
        f"Type non sérialisable : {type(value).__name__}"
    )


def build_export_payload(
    program,
    profile,
    personalization=None,
    competition_personalization=None,
) -> dict[str, Any]:
    """Ajoute les propriétés calculées utiles à l’interface."""
    payload = asdict(program)
    if personalization is not None:
        payload["history_personalization"] = asdict(
            personalization
        )

    if competition_personalization is not None:
        payload["competition_personalization"] = asdict(
            competition_personalization
        )

    physiological = profile.physiological
    vma_estimated_from_vo2 = (
        round(physiological.vo2_max / 3.5, 2)
        if physiological.vo2_max is not None
        else None
    )

    sv1_speed = (
        physiological.sv1.speed_kmh
        or (
            round(physiological.vma_kmh * 0.75, 1)
            if physiological.vma_kmh is not None
            else None
        )
    )
    sv1_heart_rate = (
        physiological.sv1.heart_rate_bpm
        or (
            round(
                physiological.threshold_heart_rate_bpm
                * 0.86
            )
            if (
                physiological.threshold_heart_rate_bpm
                is not None
            )
            else (
                round(
                    physiological.maximum_heart_rate_bpm
                    * 0.75
                )
                if (
                    physiological.maximum_heart_rate_bpm
                    is not None
                )
                else None
            )
        )
    )
    sv2_speed = (
        physiological.sv2.speed_kmh
        or physiological.threshold_speed_kmh
    )
    sv2_heart_rate = (
        physiological.sv2.heart_rate_bpm
        or physiological.threshold_heart_rate_bpm
    )

    payload["duration_weeks"] = (
        program.duration_weeks
    )
    payload["total_workouts"] = (
        program.total_workouts
    )
    payload["total_running_workouts"] = (
        program.total_running_workouts
    )
    payload["goal"]["target_pace_seconds_per_km"] = (
        program.goal.target_pace_seconds_per_km
    )
    payload["athlete_snapshot"] = {
        "age_years": physiological.age_years,
        "sex": physiological.sex,
        "vo2_max": physiological.vo2_max,
        "vma_kmh": physiological.vma_kmh,
        "vma_training_reference_kmh": (
            physiological.vma_kmh
        ),
        "vma_estimated_from_vo2_kmh": (
            vma_estimated_from_vo2
        ),
        "maximum_heart_rate_bpm": (
            physiological.maximum_heart_rate_bpm
        ),
        "resting_heart_rate_bpm": (
            physiological.resting_heart_rate_bpm
        ),
        "sv1": {
            "speed_kmh": sv1_speed,
            "heart_rate_bpm": sv1_heart_rate,
            "status": (
                "longitudinal"
                if physiological.sv1.speed_kmh is not None
                else "estimated"
            ),
        },
        "sv2": {
            "speed_kmh": sv2_speed,
            "heart_rate_bpm": sv2_heart_rate,
            "status": (
                "longitudinal"
                if sv2_speed is not None
                else "missing"
            ),
        },
        "profile_confidence_score": (
            profile.profile_confidence_score
        ),
        "data_quality_score": (
            profile.data_quality_score
        ),
    }
    return payload


def write_program(
    program,
    profile,
    output_path: str,
    personalization=None,
    competition_personalization=None,
) -> Path:
    """Enregistre le programme dans l’espace privé."""
    destination = Path(output_path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    payload = build_export_payload(
        program,
        profile,
        personalization,
        competition_personalization,
    )

    with destination.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            payload,
            output_file,
            ensure_ascii=False,
            indent=2,
            default=json_default,
        )

    return destination


def display_program(
    program,
    destination: Path,
) -> None:
    """Affiche une synthèse lisible du programme."""
    research_types = {
        WorkoutType.HILL_SPRINTS,
        WorkoutType.MIXED_THRESHOLD_VO2,
        WorkoutType.TRIANGULAR_VO2,
    }
    historical_count = sum(
        workout.sport == "running"
        and any(
            "histor" in note.lower()
            or "préparation comparable réussie"
            in note.lower()
            for note in workout.coach_notes
        )
        for week in program.weeks
        for workout in week.workouts
    )
    research_count = sum(
        workout.workout_type in research_types
        and not any(
            "histor" in note.lower()
            or "préparation comparable réussie"
            in note.lower()
            for note in workout.coach_notes
        )
        for week in program.weeks
        for workout in week.workouts
    )

    print("=" * 72)
    print(
        "ATLAS COACH - HISTORIQUE PERSONNEL + ATLAS RESEARCH"
    )
    print("=" * 72)
    print(f"Athlète : {program.athlete_id}")
    print(f"Objectif : {program.goal.name}")
    print(
        f"Échéance : {program.goal.event_date.isoformat()}"
    )
    print(
        f"Distance : {program.goal.distance_km} km"
    )
    print(
        f"Temps cible : "
        f"{program.goal.target_time_minutes} minutes"
    )
    print(f"Durée : {program.duration_weeks} semaines")
    print(
        f"Séances totales : {program.total_workouts}"
    )
    print(
        f"Séances de course : "
        f"{program.total_running_workouts}"
    )
    print(
        "Séances historiques personnalisées : "
        f"{historical_count}"
    )
    print(
        f"Séances Atlas Research génériques : {research_count}"
    )

    print()
    print("PHASES")

    for week in program.weeks:
        print(
            f"  S{week.week_number:02d} "
            f"{week.phase.value:<12} "
            f"{len(week.workouts)} séances"
        )

    print()
    print("AVERTISSEMENTS")

    if program.warnings:
        for warning in program.warnings:
            print(f"  ! {warning}")
    else:
        print("  Aucun avertissement.")

    print()
    print(f"Programme privé : {destination}")
    print("=" * 72)


def main() -> None:
    """Lance la génération réelle."""
    arguments = parse_arguments()
    profile = build_profile(arguments)
    personalization = apply_training_history(
        profile,
        arguments.training_history_fusion,
    )
    goal = PerformanceGoal(
        name=arguments.goal_name,
        event_date=date.fromisoformat(
            arguments.event_date
        ),
        distance_km=arguments.distance_km,
        target_time_minutes=(
            arguments.target_time_minutes
        ),
    )
    competition_personalization = (
        build_competition_personalization(
            arguments.competition_comparison,
            goal.distance_km,
        )
    )
    historical_progression = build_historical_progression(
        arguments.detailed_fit_history,
        arguments.competition_comparison,
        profile,
        goal,
    )
    settings = build_settings(
        arguments,
        profile,
        personalization,
        competition_personalization,
    )
    dynamic_metrics = set()

    if arguments.recovery_status_available:
        dynamic_metrics.add("recovery_status")

    program = TrainingProgramGenerator().generate(
        profile=profile,
        goal=goal,
        start_date=date.fromisoformat(
            arguments.start_date
        ),
        settings=settings,
        available_dynamic_metrics=dynamic_metrics,
        historical_progression=historical_progression,
    )
    if personalization is not None:
        program.explanation += (
            " Programme personnalisé avec la mémoire FIT + "
            "Wellness et les réponses observées à 24–72 heures."
        )
        program.warnings = list(dict.fromkeys(
            program.warnings + personalization.warnings
        ))
        if program.weeks:
            program.weeks[0].coach_notes.extend(
                personalization.explanations
            )
    destination = write_program(
        program,
        profile,
        arguments.output,
        personalization,
        competition_personalization,
    )
    display_program(
        program,
        destination,
    )


if __name__ == "__main__":
    main()