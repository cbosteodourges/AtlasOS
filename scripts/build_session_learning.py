"""
ATLAS OS
Construit la mémoire individuelle des empreintes de séances.
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
    SessionFingerprintBuilder,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de la commande."""
    parser = argparse.ArgumentParser(
        description=(
            "Construit les empreintes individuelles "
            "des séances Garmin."
        )
    )
    parser.add_argument(
        "--athlete-id",
        default="christophe",
        help="Identifiant privé de l'athlète.",
    )
    parser.add_argument(
        "--activities",
        default="atlas-data/garmin/Activities.csv",
        help="Historique CSV Garmin.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "session-learning.json"
        ),
        help="Mémoire privée à générer.",
    )
    return parser.parse_args()


def load_activities(
    csv_path: str,
) -> List[LongitudinalActivity]:
    """Charge et normalise l'historique Garmin."""
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


def json_default(value: Any) -> str:
    """Convertit les dates pour le JSON."""
    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(
        f"Type non sérialisable : {type(value)}"
    )


def write_learning(
    learning,
    output_path: str,
) -> Path:
    """Enregistre la mémoire privée."""
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
            asdict(learning),
            output_file,
            ensure_ascii=False,
            indent=2,
            default=json_default,
        )

    return destination


def format_optional(
    value,
    unit: str = "",
) -> str:
    """Formate une valeur facultative."""
    if value is None:
        return "non disponible"

    return f"{value}{unit}"


def display_learning(
    learning,
    destination: Path,
) -> None:
    """Affiche la mémoire individuelle."""
    print("=" * 76)
    print("ATLAS OS - EMPREINTES INDIVIDUELLES DE SÉANCES")
    print("=" * 76)
    print(
        "Séances transformées en empreintes : "
        f"{learning.fingerprint_count}"
    )
    print(
        "Confiance globale : "
        f"{learning.global_confidence_score}/100"
    )

    print()
    print("TOLÉRANCE IMMÉDIATE PAR TYPE DE SÉANCE")

    for result in learning.session_type_effectiveness:
        print()
        print(
            f"  {result.session_type.upper()} "
            f"({result.session_count} séance(s))"
        )
        print(
            "    Distance moyenne : "
            f"{result.average_distance_km} km"
        )
        print(
            "    Durée moyenne : "
            f"{result.average_duration_minutes} min"
        )
        print(
            "    Charge externe : "
            f"{result.average_external_load_score}/100"
        )
        print(
            "    Charge interne : "
            f"{result.average_internal_load_score}/100"
        )
        print(
            "    Intensité : "
            f"{result.average_intensity_score}/100"
        )
        print(
            "    RPE moyen : "
            f"{format_optional(result.average_perceived_effort, '/10')}"
        )
        print(
            "    Ressenti moyen : "
            f"{format_optional(result.average_feeling_score, '/100')}"
        )
        print(
            "    Réponse immédiate : "
            f"{format_optional(result.average_immediate_response_score, '/100')}"
        )
        print(
            "    Tolérance immédiate provisoire : "
            f"{result.effectiveness_score}/100"
        )
        print(
            "    Confiance : "
            f"{result.confidence_score}/100"
        )

        for signal in result.positive_signals:
            print(f"    + {signal}")

        for signal in result.warning_signals:
            print(f"    ! {signal}")

    print()
    print("DONNÉES MANQUANTES DANS LES EMPREINTES")

    missing_counts = {}

    for fingerprint in learning.fingerprints:
        for label in fingerprint.missing_data:
            missing_counts[label] = (
                missing_counts.get(label, 0)
                + 1
            )

    if missing_counts:
        for label, count in sorted(
            missing_counts.items()
        ):
            print(
                f"  ! {label} : "
                f"{count} séance(s)"
            )
    else:
        print("  Aucune donnée majeure manquante.")

    print()
    print("CONCLUSIONS")

    for conclusion in learning.conclusions:
        print(f"  + {conclusion}")

    print()
    print(f"Mémoire privée : {destination}")
    print("=" * 76)


def main() -> None:
    """Construit la mémoire individuelle."""
    arguments = parse_arguments()
    activities = load_activities(
        arguments.activities
    )

    builder = SessionFingerprintBuilder()
    learning = builder.build_learning(
        athlete_id=arguments.athlete_id,
        activities=activities,
    )
    destination = write_learning(
        learning,
        arguments.output,
    )
    display_learning(
        learning,
        destination,
    )


if __name__ == "__main__":
    main()