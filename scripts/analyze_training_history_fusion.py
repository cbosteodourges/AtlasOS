"""
ATLAS OS
Analyse fusionnée des séances FIT et de la récupération.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors.garmin_wellness import (  # noqa: E402
    GarminWellnessConnector,
)
from src.training.training_history_fusion import (  # noqa: E402
    TrainingHistoryFusionAnalyzer,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de l'analyse fusionnée."""
    parser = argparse.ArgumentParser(
        description=(
            "Relie les activités FIT aux réponses "
            "Garmin Wellness à 24–72 heures."
        )
    )
    parser.add_argument(
        "--executions",
        default=(
            "atlas-data/private/"
            "atlas-coach-executions.json"
        ),
        help="Historique privé des analyses FIT.",
    )
    parser.add_argument(
        "--wellness",
        default=(
            "atlas-data/garmin/"
            "wellness-archives"
        ),
        help="Dossier des archives Wellness.",
    )
    parser.add_argument(
        "--wellness-cache",
        default=(
            "atlas-data/private/"
            "garmin-wellness-snapshot-cache.json"
        ),
        help="Cache privé des journées Wellness déjà décodées.",
    )
    parser.add_argument(
        "--contexts",
        default=(
            "atlas-data/private/"
            "activity-contexts.json"
        ),
        help="Corrections déclarées par l'utilisateur.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "training-history-fusion.json"
        ),
        help="Mémoire fusionnée à générer.",
    )
    parser.add_argument(
        "--analysis-date",
        default=None,
        help="Date ISO utilisée pour la charge actuelle.",
    )
    return parser.parse_args()


def load_json(path: str) -> Any:
    """Charge un fichier JSON."""
    source = Path(path)
    with source.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def load_contexts(path: str) -> dict[str, dict[str, Any]]:
    """Charge les corrections facultatives."""
    source = Path(path)
    if not source.exists():
        return {}

    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(
            "Les contextes doivent former un objet JSON."
        )

    return {
        str(key): dict(value)
        for key, value in payload.items()
        if isinstance(value, dict)
    }


def write_json_atomic(
    path: str,
    payload: dict[str, Any],
) -> Path:
    """Écrit le résultat sans risque de fichier partiel."""
    destination = Path(path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            payload,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    temporary.replace(destination)
    return destination


def main() -> None:
    """Lance l'analyse fusionnée."""
    arguments = parse_arguments()

    executions = load_json(arguments.executions)
    if not isinstance(executions, list):
        raise ValueError(
            "L'historique FIT doit être une liste."
        )

    wellness = GarminWellnessConnector(
        arguments.wellness
    ).import_all_cached(
        arguments.wellness_cache
    )

    analysis_day = (
        date.fromisoformat(arguments.analysis_date)
        if arguments.analysis_date
        else None
    )

    result = TrainingHistoryFusionAnalyzer().analyze(
        executions,
        wellness,
        contexts=load_contexts(arguments.contexts),
        analysis_date=analysis_day,
    )
    destination = write_json_atomic(
        arguments.output,
        result.to_dict(),
    )

    print()
    print("ANALYSE FIT + WELLNESS")
    print("=" * 64)
    print(f"Activités fusionnées : {result.activity_count}")
    print(
        f"Journées Wellness : "
        f"{result.wellness_day_count}"
    )
    print(
        f"Couverture : "
        f"{result.wellness_coverage_percent:.1f} %"
    )
    print(
        f"Charge 7 jours : "
        f"{result.acute_load_7d:.1f}"
    )
    print(
        f"Référence 28 jours : "
        f"{result.chronic_load_28d_weekly:.1f}"
    )
    print(
        f"Ratio descriptif : "
        f"{result.acute_chronic_load_ratio}"
    )

    print()
    print("RÉPONSES PAR SPORT")
    print("-" * 64)
    for sport in result.sports:
        print(
            f"{sport.sport} : "
            f"{sport.activity_count} activité(s) | "
            f"{sport.total_duration_hours:.1f} h | "
            f"réponse 24 h {sport.average_response_24h} | "
            f"récupération {sport.average_recovery_hours} h"
        )

    print()
    print("INTERPRÉTATION")
    print("-" * 64)
    for explanation in result.explanations:
        print(f"- {explanation}")

    for warning in result.warnings:
        print(f"- Vigilance : {warning}")

    print()
    print(f"Mémoire privée : {destination}")


if __name__ == "__main__":
    main()