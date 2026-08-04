"""
ATLAS OS
Analyse les préparations des compétitions confirmées.
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
    CompetitionComparison,
    CompetitionEvent,
    CompetitionPreparationAnalyzer,
    LongitudinalActivity,
    LongitudinalActivityAdapter,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de la commande."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare les préparations précédant "
            "les compétitions Garmin."
        )
    )
    parser.add_argument(
        "--activities",
        default="atlas-data/garmin/Activities.csv",
        help="Historique CSV Garmin.",
    )
    parser.add_argument(
        "--events",
        default=(
            "atlas-data/private/"
            "competition-events.json"
        ),
        help="Compétitions confirmées.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "garmin-competition-comparison.json"
        ),
        help="Analyse privée à générer.",
    )
    return parser.parse_args()


def load_activities(
    csv_path: str,
) -> List[LongitudinalActivity]:
    """Charge l'historique Garmin longitudinal."""
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


def event_datetime(value: str) -> datetime:
    """Convertit une date selon le fuseau local."""
    parsed_date = date.fromisoformat(value)

    return datetime.combine(
        parsed_date,
        time.min,
    ).astimezone()


def load_events(
    events_path: str,
) -> List[CompetitionEvent]:
    """Charge les compétitions confirmées."""
    with Path(events_path).open(
        "r",
        encoding="utf-8",
    ) as input_file:
        payload = json.load(input_file)

    events: List[CompetitionEvent] = []

    for item in payload.get("events", []):
        environment = item.get(
            "environment",
            {},
        )

        events.append(
            CompetitionEvent(
                event_date=event_datetime(
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

    return events


def optional_float(
    value: Any,
) -> Optional[float]:
    """Convertit une valeur facultative."""
    if value is None:
        return None

    return float(value)


def json_default(value: Any) -> str:
    """Convertit les dates pour le JSON."""
    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(
        f"Type non sérialisable : {type(value)}"
    )


def write_comparison(
    comparison: CompetitionComparison,
    output_path: str,
) -> Path:
    """Enregistre l'analyse comparative privée."""
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
            asdict(comparison),
            output_file,
            ensure_ascii=False,
            indent=2,
            default=json_default,
        )

    return destination


def format_optional(
    value: Optional[float],
    unit: str = "",
) -> str:
    """Formate une valeur facultative."""
    if value is None:
        return "non disponible"

    return f"{value}{unit}"


def display_window(
    label: str,
    window,
) -> None:
    """Affiche une fenêtre de préparation."""
    print()
    print(f"  {label}")

    print(
        "    Volume course : "
        f"{window.running_distance_km} km"
    )
    print(
        "    Volume hebdomadaire : "
        f"{window.average_running_distance_per_week_km} "
        "km/semaine"
    )
    print(
        "    Fréquence : "
        f"{window.average_running_sessions_per_week} "
        "courses/semaine"
    )
    print(
        "    Sortie la plus longue : "
        f"{window.longest_running_activity_km} km"
    )
    print(
        "    Sorties longues : "
        f"{window.long_run_count}"
    )
    print(
        "    Séances intenses : "
        f"{window.high_intensity_session_count}"
    )
    print(
        "      Tempo : "
        f"{window.tempo_session_count}"
    )
    print(
        "      Seuil : "
        f"{window.threshold_session_count}"
    )
    print(
        "      VO2 max : "
        f"{window.vo2_session_count}"
    )
    print(
        "      Fractionné : "
        f"{window.interval_session_count}"
    )
    print(
        "    Efficacité aérobie : "
        f"{format_optional(window.average_aerobic_efficiency)}"
    )
    print(
        "    Effort perçu moyen : "
        f"{format_optional(window.average_perceived_effort, '/10')}"
    )
    print(
        "    Ressenti moyen : "
        f"{format_optional(window.average_feeling_score, '/100')}"
    )


def display_adaptive_period(
    adaptive_period,
) -> None:
    """Affiche la période de préparation détectée."""
    print()
    print("  PÉRIODE ADAPTATIVE DÉTECTÉE")

    if adaptive_period is None:
        print(
            "    Analyse adaptative non disponible."
        )
        return

    print(
        "    Début détecté : "
        f"{adaptive_period.detected_start_at.date()}"
    )
    print(
        "    Durée pertinente : "
        f"{adaptive_period.duration_weeks} semaines "
        f"({adaptive_period.duration_days} jours)"
    )
    print(
        "    Historique disponible : "
        f"{adaptive_period.available_history_weeks} "
        "semaines"
    )
    print(
        "    Confiance de la détection : "
        f"{adaptive_period.confidence_score}/100"
    )
    print(
        "    Historique limité : "
        f"{'oui' if adaptive_period.data_limited else 'non'}"
    )

    print("    Raisons :")

    for reason in adaptive_period.detection_reasons:
        print(f"      - {reason}")

    print("    Phases détectées :")

    phase_labels = {
        "base": "Base",
        "specific": "Spécifique",
        "taper": "Affûtage",
    }

    for phase in adaptive_period.phases:
        label = phase_labels.get(
            phase.phase_name,
            phase.phase_name,
        )
        print(
            f"      - {label} : "
            f"{phase.start_at.date()} au "
            f"{phase.end_at.date()} | "
            f"{phase.duration_days} jours | "
            f"{phase.running_distance_km} km | "
            f"{phase.high_intensity_session_count} "
            "séance(s) intense(s) | "
            f"{phase.long_run_count} sortie(s) longue(s)"
        )


def display_comparison(
    comparison: CompetitionComparison,
    destination: Path,
) -> None:
    """Affiche l'analyse des compétitions."""
    print("=" * 76)
    print(
        "ATLAS OS - ANALYSE DES PRÉPARATIONS "
        "DE COMPÉTITION"
    )
    print("=" * 76)

    for analysis in comparison.analyses:
        event = analysis.event

        print()
        print("-" * 76)
        print(
            f"{event.event_date.date()} | "
            f"{event.title} | "
            f"{event.distance_km} km"
        )
        print(
            "Résultat utilisateur : "
            f"{event.outcome_label}"
        )
        print(
            "Score de préparation ATLAS : "
            f"{analysis.preparation_score}/100"
        )

        display_adaptive_period(
            analysis.adaptive_period
        )

        display_window(
            "12 SEMAINES",
            analysis.twelve_week_window,
        )
        display_window(
            "8 SEMAINES SPÉCIFIQUES",
            analysis.eight_week_window,
        )
        display_window(
            "4 DERNIÈRES SEMAINES",
            analysis.four_week_window,
        )
        display_window(
            "DERNIÈRE SEMAINE",
            analysis.final_week_window,
        )

        print()
        print("  AFFÛTAGE")

        taper = analysis.taper

        print(
            "    Volume dernière semaine : "
            f"{taper.final_week_running_distance_km} km"
        )
        print(
            "    Moyenne des 3 semaines précédentes : "
            f"{taper.previous_three_week_average_km} km"
        )
        print(
            "    Variation du volume : "
            f"{format_optional(taper.volume_change_percent, ' %')}"
        )
        print(
            "    Dernière course avant compétition : "
            f"{format_optional(taper.days_since_last_run, ' jour(s)')}"
        )
        print(
            "    Dernière sortie longue : "
            f"{format_optional(taper.days_since_last_long_run, ' jour(s)')}"
        )
        print(
            "    Dernière séance intense : "
            f"{format_optional(taper.days_since_last_intensity_session, ' jour(s)')}"
        )

        print()
        print("  POINTS FAVORABLES")

        if analysis.strengths:
            for strength in analysis.strengths:
                print(f"    + {strength}")
        else:
            print(
                "    Aucun point favorable confirmé."
            )

        print()
        print("  POINTS DE VIGILANCE")

        if analysis.warnings:
            for warning in analysis.warnings:
                print(f"    ! {warning}")
        else:
            print("    Aucun signal majeur.")

        print()
        print("  HYPOTHÈSES")

        for hypothesis in analysis.hypotheses:
            print(f"    ? {hypothesis}")

    print()
    print("=" * 76)
    print("COMPARAISON RÉUSSITES / ÉCHEC")
    print("=" * 76)

    print()
    print("FACTEURS COMMUNS AUX RÉUSSITES")

    if comparison.common_success_factors:
        for factor in comparison.common_success_factors:
            print(f"  + {factor}")
    else:
        print("  Aucun facteur encore confirmé.")

    print()
    print("FACTEURS DE RISQUE DE L'ÉCHEC")

    if comparison.failure_risk_factors:
        for factor in comparison.failure_risk_factors:
            print(f"  ! {factor}")
    else:
        print("  Aucun facteur encore confirmé.")

    print()
    print("CONCLUSIONS PROVISOIRES")

    for conclusion in comparison.conclusions:
        print(f"  ? {conclusion}")

    print()
    print(f"Analyse privée : {destination}")
    print("=" * 76)


def main() -> None:
    """Lance l'analyse des préparations."""
    arguments = parse_arguments()

    activities = load_activities(
        arguments.activities
    )
    events = load_events(
        arguments.events
    )

    analyzer = CompetitionPreparationAnalyzer()
    comparison = analyzer.compare(
        activities,
        events,
    )
    destination = write_comparison(
        comparison,
        arguments.output,
    )
    display_comparison(
        comparison,
        destination,
    )


if __name__ == "__main__":
    main()