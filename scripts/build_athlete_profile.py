"""
ATLAS OS
Construit le profil sportif adaptatif de l'utilisateur.
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors.garmin_history import (  # noqa: E402
    GarminHistoryConnector,
)
from src.performance import (  # noqa: E402
    AthleteProfile,
    AthleteProfileBuilder,
    CompetitionEvent,
    LongitudinalActivity,
    LongitudinalActivityAdapter,
    PhysiologicalReferences,
    TrainingAvailability,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les chemins utilisés par la commande."""
    parser = argparse.ArgumentParser(
        description=(
            "Construit le profil sportif adaptatif ATLAS."
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
        help="Informations déclarées par l'utilisateur.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "athlete-profile.json"
        ),
        help="Profil adaptatif privé à générer.",
    )
    return parser.parse_args()


def load_activities(
    csv_path: str,
) -> List[LongitudinalActivity]:
    """Charge et adapte l'historique Garmin."""
    connector = GarminHistoryConnector(csv_path)
    connector.connect()

    adapter = LongitudinalActivityAdapter()
    activities: List[LongitudinalActivity] = []

    for raw_activity in connector.fetch_activities():
        normalized = connector.normalize(
            raw_activity
        )
        activities.append(
            adapter.adapt(normalized)
        )

    return activities


def local_event_datetime(
    value: str,
) -> datetime:
    """Convertit une date dans le fuseau local."""
    parsed_date = date.fromisoformat(value)

    return datetime.combine(
        parsed_date,
        time.min,
    ).astimezone()


def optional_float(
    value: Any,
) -> Optional[float]:
    """Convertit une valeur numérique facultative."""
    if value is None:
        return None

    return float(value)


def load_competitions(
    path: str,
) -> List[CompetitionEvent]:
    """Charge les compétitions confirmées."""
    source = Path(path)

    if not source.exists():
        return []

    with source.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        payload = json.load(input_file)

    competitions: List[CompetitionEvent] = []

    for item in payload.get("events", []):
        environment = item.get(
            "environment",
            {},
        )

        competitions.append(
            CompetitionEvent(
                event_date=local_event_datetime(
                    item["date"]
                ),
                title=str(item["title"]),
                distance_km=float(
                    item["distance_km"]
                ),
                outcome=str(item["outcome"]),
                outcome_label=str(
                    item["outcome_label"]
                ),
                failure_at_km=optional_float(
                    item.get("failure_at_km")
                ),
                difficulty_from_km=optional_float(
                    item.get("difficulty_from_km")
                ),
                heat_level=environment.get(
                    "heat"
                ),
                elevation_context=environment.get(
                    "elevation"
                ),
                notes=str(item.get("notes") or ""),
            )
        )

    return competitions


def load_declared_profile(
    path: str,
) -> dict:
    """Charge les informations déclarées."""
    with Path(path).open(
        "r",
        encoding="utf-8",
    ) as input_file:
        return json.load(input_file)


def build_physiological(
    payload: dict,
) -> PhysiologicalReferences:
    """Construit les références physiologiques."""
    values = payload.get(
        "physiological",
        {},
    )

    return PhysiologicalReferences(
        age_years=values.get("age_years"),
        sex=values.get("sex"),
        height_cm=optional_float(
            values.get("height_cm")
        ),
        weight_kg=optional_float(
            values.get("weight_kg")
        ),
        maximum_heart_rate_bpm=optional_float(
            values.get(
                "maximum_heart_rate_bpm"
            )
        ),
        resting_heart_rate_bpm=optional_float(
            values.get(
                "resting_heart_rate_bpm"
            )
        ),
        threshold_heart_rate_bpm=optional_float(
            values.get(
                "threshold_heart_rate_bpm"
            )
        ),
        vma_kmh=optional_float(
            values.get("vma_kmh")
        ),
        vo2_max=optional_float(
            values.get("vo2_max")
        ),
        threshold_speed_kmh=optional_float(
            values.get(
                "threshold_speed_kmh"
            )
        ),
        hrv_baseline_ms=optional_float(
            values.get("hrv_baseline_ms")
        ),
        body_battery_baseline=optional_float(
            values.get(
                "body_battery_baseline"
            )
        ),
    )


def build_availability(
    payload: dict,
) -> TrainingAvailability:
    """Construit les disponibilités déclarées."""
    values = payload.get(
        "availability",
        {},
    )

    return TrainingAvailability(
        available_days_per_week=values.get(
            "available_days_per_week"
        ),
        preferred_training_days=list(
            values.get(
                "preferred_training_days",
                [],
            )
        ),
        unavailable_days=list(
            values.get(
                "unavailable_days",
                [],
            )
        ),
        maximum_weekly_hours=optional_float(
            values.get(
                "maximum_weekly_hours"
            )
        ),
        professional_constraints=str(
            values.get(
                "professional_constraints"
            )
            or ""
        ),
        family_constraints=str(
            values.get("family_constraints")
            or ""
        ),
    )


def write_profile(
    profile: AthleteProfile,
    output_path: str,
) -> Path:
    """Enregistre le profil privé."""
    destination = Path(output_path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            asdict(profile),
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    return destination


def display_profile(
    profile: AthleteProfile,
    destination: Path,
) -> None:
    """Affiche la synthèse du profil."""
    print("=" * 72)
    print("ATLAS OS - PROFIL SPORTIF ADAPTATIF")
    print("=" * 72)

    print(
        f"Niveau déclaré : "
        f"{profile.declared_level}"
    )
    print(
        f"Niveau observé : "
        f"{profile.observed_level}"
    )
    print(
        f"Confiance du profil : "
        f"{profile.profile_confidence_score}/100"
    )
    print(
        f"Qualité des données : "
        f"{profile.data_quality_score}/100"
    )
    print(
        f"Historique : "
        f"{profile.history_activity_count} activités "
        f"sur {profile.history_duration_weeks} semaines"
    )
    print(
        f"Compétitions confirmées : "
        f"{profile.competition_count}"
    )
    print(
        f"Compétitions réussies : "
        f"{profile.successful_competition_count}"
    )

    print()
    print("TOLÉRANCE OBSERVÉE")

    tolerance = profile.tolerance

    print(
        "  Volume habituel : "
        f"{tolerance.usual_running_distance_per_week_km} "
        "km/semaine"
    )
    print(
        "  Fréquence habituelle : "
        f"{tolerance.usual_running_sessions_per_week} "
        "courses/semaine"
    )
    print(
        "  Volume hebdomadaire maximal observé : "
        f"{tolerance.maximum_observed_weekly_distance_km} km"
    )
    print(
        "  Volume hebdomadaire toléré estimé : "
        f"{tolerance.maximum_tolerated_weekly_distance_km} km"
    )
    print(
        "  Séances intenses habituelles : "
        f"{tolerance.usual_high_intensity_sessions_per_week} "
        "par semaine"
    )
    print(
        "  Sorties longues habituelles : "
        f"{tolerance.usual_long_runs_per_month} "
        "par mois"
    )
    print(
        "  Évolution récente de la charge : "
        f"{tolerance.recent_load_change_percent} %"
    )

    print()
    print("RÉFÉRENCES PHYSIOLOGIQUES")

    physiological = profile.physiological

    print(
        f"  VMA : "
        f"{physiological.vma_kmh} km/h"
    )
    print(
        f"  VO2 max : "
        f"{physiological.vo2_max}"
    )
    print(
        "  Vitesse au seuil : "
        f"{physiological.threshold_speed_kmh} km/h"
    )
    print(
        "  FC au seuil : "
        f"{physiological.threshold_heart_rate_bpm} bpm"
    )

    print()
    print("POINTS FORTS")

    for strength in profile.strengths:
        print(f"  + {strength}")

    print()
    print("DONNÉES MANQUANTES")

    if profile.missing_data:
        for missing in profile.missing_data:
            print(f"  ! {missing}")
    else:
        print("  Aucune donnée essentielle manquante.")

    print()
    print(f"Profil privé : {destination}")
    print("=" * 72)


def main() -> None:
    """Lance la construction du profil."""
    arguments = parse_arguments()

    declared = load_declared_profile(
        arguments.profile_input
    )
    activities = load_activities(
        arguments.activities
    )
    competitions = load_competitions(
        arguments.competitions
    )

    builder = AthleteProfileBuilder()
    profile = builder.build(
        athlete_id=str(
            declared["athlete_id"]
        ),
        declared_level=str(
            declared["declared_level"]
        ),
        activities=activities,
        competitions=competitions,
        physiological=build_physiological(
            declared
        ),
        availability=build_availability(
            declared
        ),
        training_age_years=optional_float(
            declared.get(
                "training_age_years"
            )
        ),
    )

    destination = write_profile(
        profile,
        arguments.output,
    )
    display_profile(
        profile,
        destination,
    )


if __name__ == "__main__":
    main()