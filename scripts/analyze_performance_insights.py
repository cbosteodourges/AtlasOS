"""
ATLAS OS
Analyse comparative des performances Garmin.
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors.garmin_history import (  # noqa: E402
    GarminHistoryConnector,
)
from src.performance import (  # noqa: E402
    LongitudinalActivity,
    LongitudinalActivityAdapter,
    PerformanceInsightAnalysis,
    PerformanceInsightAnalyzer,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de la commande."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare les périodes et les meilleures "
            "performances de l'historique Garmin."
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
            "garmin-performance-insights.json"
        ),
        help="Fichier JSON privé à générer.",
    )
    return parser.parse_args()


def load_activities(
    input_path: str,
) -> List[LongitudinalActivity]:
    """Importe et adapte les activités Garmin."""
    connector = GarminHistoryConnector(
        input_path
    )
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


def json_default(value: Any) -> str:
    """Convertit les dates pour le JSON."""
    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(
        f"Type non sérialisable : {type(value)}"
    )


def write_analysis(
    analysis: PerformanceInsightAnalysis,
    output_path: str,
) -> Path:
    """Enregistre l'analyse comparative."""
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


def format_pace(
    pace_seconds: Optional[float],
) -> str:
    """Formate une allure en minutes par kilomètre."""
    if pace_seconds is None:
        return "non disponible"

    rounded_seconds = round(pace_seconds)
    minutes = rounded_seconds // 60
    seconds = rounded_seconds % 60

    return f"{minutes}'{seconds:02d}/km"


def format_value(
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
    """Affiche une période d'entraînement."""
    print()
    print(label)

    if window.start_at and window.end_at:
        print(
            f"  Période : "
            f"{window.start_at.date()} "
            f"au {window.end_at.date()}"
        )

    print(
        f"  Courses : "
        f"{window.running_activity_count}"
    )
    print(
        f"  Volume total : "
        f"{window.total_running_distance_km} km"
    )
    print(
        f"  Volume moyen : "
        f"{window.average_running_distance_per_week_km} "
        f"km/semaine"
    )
    print(
        f"  Fréquence : "
        f"{window.average_running_sessions_per_week} "
        f"séances/semaine"
    )
    print(
        f"  Distance moyenne : "
        f"{format_value(window.average_activity_distance_km, ' km')}"
    )
    print(
        f"  Vitesse moyenne : "
        f"{format_value(window.average_speed_kmh, ' km/h')}"
    )
    print(
        f"  Allure moyenne : "
        f"{format_pace(window.average_pace_seconds_per_km)}"
    )
    print(
        f"  FC moyenne : "
        f"{format_value(window.average_heart_rate_bpm, ' bpm')}"
    )
    print(
        f"  Efficacité aérobie : "
        f"{format_value(window.average_aerobic_efficiency)}"
    )
    print(
        f"  Cadence moyenne : "
        f"{format_value(window.average_cadence_spm, ' pas/min')}"
    )
    print(
        f"  Longueur de foulée : "
        f"{format_value(window.average_stride_length_m, ' m')}"
    )
    print(
        f"  Puissance moyenne : "
        f"{format_value(window.average_power_watts, ' W')}"
    )
    print(
        f"  Body Battery consommé : "
        f"{format_value(window.average_body_battery_impact)}"
    )
    print(
        f"  Qualité des données : "
        f"{window.data_quality_score}/100"
    )


def display_analysis(
    analysis: PerformanceInsightAnalysis,
    destination: Path,
) -> None:
    """Affiche les tendances et références."""
    print("=" * 72)
    print("ATLAS OS - COMPARAISON DES PERFORMANCES")
    print("=" * 72)

    display_window(
        "8 PREMIÈRES SEMAINES",
        analysis.early_window,
    )
    display_window(
        "8 DERNIÈRES SEMAINES",
        analysis.recent_window,
    )

    print()
    print("ÉVOLUTION ENTRE LES DEUX PÉRIODES")
    print(
        "  Vitesse moyenne : "
        f"{format_value(analysis.average_speed_change_percent, ' %')}"
    )
    print(
        "  Amélioration de l'allure : "
        f"{format_value(analysis.pace_change_percent, ' %')}"
    )
    print(
        "  Fréquence cardiaque moyenne : "
        f"{format_value(analysis.average_heart_rate_change_percent, ' %')}"
    )
    print(
        "  Efficacité aérobie : "
        f"{format_value(analysis.aerobic_efficiency_change_percent, ' %')}"
    )
    print(
        "  Cadence : "
        f"{format_value(analysis.cadence_change_percent, ' %')}"
    )
    print(
        "  Longueur de foulée : "
        f"{format_value(analysis.stride_length_change_percent, ' %')}"
    )
    print(
        "  Puissance : "
        f"{format_value(analysis.power_change_percent, ' %')}"
    )

    print()
    print("MEILLEURES RÉFÉRENCES OBSERVÉES")

    for benchmark in analysis.distance_benchmarks:
        print()
        print(
            f"  {benchmark.label} "
            f"({benchmark.activity_count} activités comparables)"
        )

        if benchmark.best_activity_at is None:
            print("    Aucune référence disponible.")
            continue

        print(
            f"    Date : "
            f"{benchmark.best_activity_at.date()}"
        )
        print(
            f"    Distance : "
            f"{benchmark.best_distance_km} km"
        )
        print(
            f"    Durée : "
            f"{benchmark.best_duration_minutes} min"
        )
        print(
            f"    Allure : "
            f"{format_pace(benchmark.best_pace_seconds_per_km)}"
        )
        print(
            f"    FC moyenne : "
            f"{format_value(benchmark.best_average_heart_rate_bpm, ' bpm')}"
        )
        print(
            f"    Efficacité aérobie : "
            f"{format_value(benchmark.best_aerobic_efficiency)}"
        )
        print(
            f"    Cadence : "
            f"{format_value(benchmark.best_average_cadence_spm, ' pas/min')}"
        )
        print(
            f"    Foulée : "
            f"{format_value(benchmark.best_average_stride_length_m, ' m')}"
        )
        print(
            f"    Puissance : "
            f"{format_value(benchmark.best_average_power_watts, ' W')}"
        )
        print(
            f"    Qualité : "
            f"{benchmark.data_quality_score}/100"
        )

    print()
    print("POINTS FAVORABLES")

    if analysis.strengths:
        for strength in analysis.strengths:
            print(f"  + {strength}")
    else:
        print("  Aucun point favorable confirmé.")

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
    print("=" * 72)


def main() -> None:
    """Lance l'analyse comparative."""
    arguments = parse_arguments()

    activities = load_activities(
        arguments.input
    )
    analyzer = PerformanceInsightAnalyzer()
    analysis = analyzer.analyse(activities)
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