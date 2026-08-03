"""
ATLAS OS
Analyse longitudinale de l'historique Garmin Connect.
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors.garmin_history import (  # noqa: E402
    GarminHistoryConnector,
)
from src.performance import (  # noqa: E402
    LongitudinalActivity,
    LongitudinalActivityAdapter,
    LongitudinalAnalysis,
    LongitudinalPerformanceAnalyzer,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de la commande."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyse l'historique CSV Garmin "
            "avec Performance Intelligence v2."
        )
    )
    parser.add_argument(
        "--input",
        default="atlas-data/garmin/Activities.csv",
        help="Chemin du fichier Activities.csv de Garmin.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "garmin-longitudinal-analysis.json"
        ),
        help="Fichier JSON privé à générer.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help=(
            "Date ISO facultative : seules les activités "
            "postérieures seront analysées."
        ),
    )
    return parser.parse_args()


def load_activities(
    input_path: str,
    since: str | None,
) -> List[LongitudinalActivity]:
    """Importe et adapte les activités Garmin."""
    connector = GarminHistoryConnector(
        input_path
    )
    connector.connect()

    adapter = LongitudinalActivityAdapter()
    longitudinal_activities: List[
        LongitudinalActivity
    ] = []

    for raw_activity in connector.fetch_activities(
        since=since
    ):
        normalized = connector.normalize(
            raw_activity
        )
        longitudinal_activities.append(
            adapter.adapt(normalized)
        )

    return longitudinal_activities


def analyze(
    activities: List[LongitudinalActivity],
) -> LongitudinalAnalysis:
    """Exécute l'analyse longitudinale."""
    analyzer = LongitudinalPerformanceAnalyzer()
    return analyzer.analyse(activities)


def json_default(value: Any) -> str:
    """Convertit les objets non JSON natifs."""
    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(
        f"Type non sérialisable : {type(value)}"
    )


def write_analysis(
    analysis: LongitudinalAnalysis,
    output_path: str,
) -> Path:
    """Enregistre l'analyse dans un JSON privé."""
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
            asdict(analysis),
            output_file,
            ensure_ascii=False,
            indent=2,
            default=json_default,
        )

    return destination


def display_analysis(
    analysis: LongitudinalAnalysis,
    destination: Path,
) -> None:
    """Affiche une synthèse lisible dans PowerShell."""
    print("=" * 68)
    print("ATLAS OS - PERFORMANCE INTELLIGENCE V2")
    print("=" * 68)

    print(
        f"Activités analysées : "
        f"{analysis.activity_count}"
    )
    print(
        f"Courses identifiées : "
        f"{analysis.running_activity_count}"
    )

    if analysis.first_activity_at:
        print(
            "Première activité : "
            f"{analysis.first_activity_at.date()}"
        )

    if analysis.last_activity_at:
        print(
            "Dernière activité : "
            f"{analysis.last_activity_at.date()}"
        )

    print(
        "Distance totale en course : "
        f"{analysis.total_running_distance_km} km"
    )
    print(
        "Volume hebdomadaire moyen : "
        f"{analysis.average_running_distance_per_week_km} km"
    )
    print(
        "Volume hebdomadaire maximal : "
        f"{analysis.maximum_running_distance_per_week_km} km"
    )
    print(
        "Séances de course par semaine : "
        f"{analysis.average_running_sessions_per_week}"
    )
    print(
        "Sortie de course la plus longue : "
        f"{analysis.longest_running_activity_km} km"
    )
    print(
        "Volume des 4 dernières semaines : "
        f"{analysis.recent_four_week_distance_km} km"
    )
    print(
        "Volume des 4 semaines précédentes : "
        f"{analysis.previous_four_week_distance_km} km"
    )

    load_change = (
        f"{analysis.recent_load_change_percent} %"
        if analysis.recent_load_change_percent
        is not None
        else "non calculable"
    )
    print(
        "Évolution récente du volume : "
        f"{load_change}"
    )
    print(
        "Qualité moyenne des données : "
        f"{analysis.data_quality_score}/100"
    )

    print()
    print("POINTS FAVORABLES")

    if analysis.strengths:
        for strength in analysis.strengths:
            print(f"  + {strength}")
    else:
        print(
            "  Aucun point favorable encore confirmé."
        )

    print()
    print("POINTS DE VIGILANCE")

    if analysis.warnings:
        for warning in analysis.warnings:
            print(f"  ! {warning}")
    else:
        print("  Aucun signal majeur détecté.")

    print()
    print("HYPOTHÈSES À APPROFONDIR")

    for hypothesis in analysis.hypotheses:
        print(f"  ? {hypothesis}")

    print()
    print(f"Analyse privée : {destination}")
    print("=" * 68)


def main() -> None:
    """Lance l'analyse de l'historique Garmin."""
    arguments = parse_arguments()

    activities = load_activities(
        arguments.input,
        arguments.since,
    )
    analysis = analyze(activities)
    destination = write_analysis(
        analysis,
        arguments.output,
    )
    display_analysis(
        analysis,
        destination,
    )


if __name__ == "__main__":
    main()