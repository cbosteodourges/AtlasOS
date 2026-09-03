"""Génère le banc d'essai Atlas sur six profils reproductibles."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from enum import Enum
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.performance.athlete_profile import (
    AthleteProfile, PhysiologicalReferences, TrainingAvailability, TrainingTolerance,
)
from src.performance.models import PerformanceGoal
from src.training.program_generator import TrainingProgramGenerator
from src.training.program_models import ProgramGenerationSettings


START = date(2026, 9, 7)
END = date(2026, 11, 29)


def profile(code, level, sessions, volume, maximum, vma, vo2, sv1, sv2,
            days, pain=False, notes=""):
    return AthleteProfile(
        athlete_id=f"benchmark-{code.lower()}", declared_level=level,
        observed_level=level, training_age_years={"beginner": .2, "regular": 1.5,
        "intermediate": 4, "competitive": 8, "nature": 5}[level],
        physiological=PhysiologicalReferences(
            vma_kmh=vma, vo2_max=vo2, threshold_speed_kmh=sv2,
        ),
        availability=TrainingAvailability(
            available_days_per_week=days,
            professional_constraints="Horaires de travail variables",
            family_constraints="Disponibilités familiales prioritaires",
        ),
        tolerance=TrainingTolerance(
            usual_running_distance_per_week_km=volume,
            usual_running_sessions_per_week=sessions,
            maximum_tolerated_weekly_distance_km=maximum,
            learned_physiological_tolerance_score=55 if level == "beginner" else 70,
            learned_biomechanical_tolerance_score=52 if level == "beginner" else 68,
        ),
        current_pain_or_injury=pain, pain_or_injury_notes=notes,
        history_activity_count=8 if level == "beginner" else int(volume * 6),
        history_duration_weeks=8 if level == "beginner" else 80,
        data_quality_score=55 if level == "beginner" else 82,
        profile_confidence_score=50 if level == "beginner" else 78,
        strengths=[f"SV1 de travail estimé à {sv1:.1f} km/h"],
        limitations=[notes] if notes else [],
    )


CASES = [
    ("A", "Débutant — premier 5 km",
     profile("A", "beginner", 2, 8, 15, 9.5, 34, 6.8, 8.0, 3),
     PerformanceGoal("Premier 5 km", END, 5, 35), 3),
    ("B", "Débutant régulier — premier 10 km",
     profile("B", "regular", 3, 18, 28, 11.2, 40, 8.0, 9.6, 4),
     PerformanceGoal("Premier 10 km", END, 10, 65), 3),
    ("C", "Intermédiaire — semi-marathon",
     profile("C", "intermediate", 4, 35, 48, 14.0, 49, 10.2, 12.6, 5),
     PerformanceGoal("Semi-marathon", END, 21.1, 105), 4),
    ("D", "Confirmé — 10 km performance",
     profile("D", "competitive", 5, 50, 65, 17.0, 60, 12.2, 15.2, 6),
     PerformanceGoal("10 km performance", END, 10, 39), 5),
    ("E", "Confirmé — marathon",
     profile("E", "competitive", 5, 65, 85, 16.2, 57, 11.6, 14.2, 6),
     PerformanceGoal("Marathon", END, 42.195, 195), 5),
    ("F", "Coureur nature — trail court",
     profile("F", "nature", 4, 38, 55, 14.2, 50, 9.8, 12.4, 5,
             notes="Ancienne sensibilité achilléenne, actuellement calme"),
     PerformanceGoal("Trail court", END, 24, 165, discipline="trail",
                     elevation_gain_m=1100, elevation_loss_m=1100,
                     terrain_technicality="moderate"), 4),
]

PERSONAS = {
    "A": {"age": 34, "sex": "femme", "occupation": "employée, deux enfants", "history": "8 semaines de course-marche", "fragility": "mollets sensibles après reprise"},
    "B": {"age": 42, "sex": "homme", "occupation": "technicien en horaires décalés", "history": "18 mois, 3 sorties par semaine", "fragility": "sommeil irrégulier"},
    "C": {"age": 39, "sex": "femme", "occupation": "cadre, vie familiale dense", "history": "4 ans, plusieurs 10 km", "fragility": "fatigue professionnelle périodique"},
    "D": {"age": 31, "sex": "homme", "occupation": "enseignant", "history": "8 ans, 10 km en 40 min", "fragility": "raideur des ischio-jambiers"},
    "E": {"age": 46, "sex": "femme", "occupation": "profession libérale", "history": "10 ans, trois marathons", "fragility": "tolérance digestive à tester"},
    "F": {"age": 37, "sex": "homme", "occupation": "infirmier", "history": "5 ans route et sentier", "fragility": "ancienne sensibilité achilléenne"},
}

ADAPTATION_SCENARIOS = [
    ("Réussite", "Conserver la structure ; n'augmenter que dans les bornes de progression et après confirmation à 24–72 h."),
    ("Fatigue", "Réduire le volume spécifique ou remplacer l'intensité par de l'endurance facile ; préserver l'objectif de la semaine."),
    ("Douleur", "Suspendre l'intensité et la charge mécanique concernée ; proposer repos, vélo doux ou avis professionnel selon gravité."),
    ("Séance manquée", "Prévisualiser le déplacement ; conserver ou remplacer la séance cible et choisir explicitement si le reste est décalé."),
]


def serial(value):
    if isinstance(value, (date, Enum)):
        return value.isoformat() if isinstance(value, date) else value.value
    raise TypeError(type(value).__name__)


def main():
    target = REPOSITORY_ROOT / "reports" / "six-profile-benchmark"
    target.mkdir(parents=True, exist_ok=True)
    summary = []
    report = [
        "# Banc d'essai Atlas — six profils de course à pied",
        "",
        "Ce document est une base de revue experte. Les fichiers JSON associés contiennent chaque séance complète et ses charges attendues.",
        "",
    ]
    generator = TrainingProgramGenerator()
    for code, label, athlete, goal, weekly_sessions in CASES:
        settings = ProgramGenerationSettings(
            running_sessions_per_week=weekly_sessions,
            optional_running_sessions_per_week=0 if code in {"A", "B"} else 1,
            strength_sessions_per_week=1 if code in {"A", "B"} else 2,
            cycling_sessions_per_week=0,
            preferred_long_run_day="sunday",
            preferred_quality_days=["tuesday", "friday"],
            maximum_weekly_progression_percent=6 if code in {"A", "B"} else 8,
        )
        program = generator.generate(
            profile=athlete, goal=goal, start_date=START, settings=settings,
            available_dynamic_metrics={"recovery_status"},
        )
        payload = {
            "profile_label": label,
            "persona": PERSONAS[code],
            "profile": asdict(athlete),
            "program": asdict(program),
            "adaptation_scenarios": [
                {"situation": situation, "atlas_response": response}
                for situation, response in ADAPTATION_SCENARIOS
            ],
        }
        (target / f"profil-{code}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=serial) + "\n",
            encoding="utf-8",
        )
        summary.append({
            "code": code, "label": label, "weeks": program.duration_weeks,
            "running_workouts": program.total_running_workouts,
            "warnings": program.warnings,
        })
        phases = []
        for week in program.weeks:
            if not phases or phases[-1] != week.phase.value:
                phases.append(week.phase.value)
        sample = next(
            (workout for week in program.weeks for workout in week.workouts
             if workout.sport == "running"),
            program.weeks[0].workouts[0],
        )
        report.extend([
            f"## Profil {code} — {label}", "",
            f"- Persona : {PERSONAS[code]['age']} ans, {PERSONAS[code]['sex']}, {PERSONAS[code]['occupation']}.",
            f"- Historique : {PERSONAS[code]['history']}.",
            f"- Fragilité : {PERSONAS[code]['fragility']}.",
            f"- Références : VO₂max {athlete.physiological.vo2_max}, VMA {athlete.physiological.vma_kmh} km/h, SV1 {athlete.strengths[0].split('à ')[-1]}, SV2 {athlete.physiological.threshold_speed_kmh} km/h.",
            f"- Disponibilité : {athlete.availability.available_days_per_week} jours ; {weekly_sessions} séances de course prescrites.",
            f"- Plan : {program.duration_weeks} semaines, {program.total_running_workouts} séances de course ; phases {' → '.join(phases)}.",
            f"- Exemple : **{sample.title}**, {sample.planned_duration_minutes or 'durée par blocs'} min — {sample.objective}",
            "- Justification : progression bornée, charge mécanique explicite, récupération attendue et spécificité croissante de l'objectif.",
            "",
        ])
        for situation, response in ADAPTATION_SCENARIOS:
            report.append(f"  - **{situation}** : {response}")
        report.append("")
    (target / "index.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (target / "REVUE.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
