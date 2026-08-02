"""
ATLAS OS
Importe les fichiers Garmin FIT vers le format JSON commun.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors import (  # noqa: E402
    ActivitySyncService,
    ConnectorRegistry,
    GarminConnector,
    NormalizedActivity,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de la commande."""
    parser = argparse.ArgumentParser(
        description=(
            "Importe les activités Garmin FIT dans ATLAS OS."
        )
    )
    parser.add_argument(
        "--input",
        default="atlas-data/garmin",
        help="Dossier contenant les fichiers FIT Garmin.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "garmin-normalized-activities.json"
        ),
        help="Fichier JSON privé à générer.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help=(
            "Date ISO facultative : seules les activités "
            "postérieures seront importées."
        ),
    )
    return parser.parse_args()


def synchronize(
    input_directory: str,
    since: str | None,
) -> List[NormalizedActivity]:
    """Exécute la chaîne commune de synchronisation Garmin."""
    registry = ConnectorRegistry()
    registry.register(
        GarminConnector(input_directory)
    )

    service = ActivitySyncService(registry)
    return service.synchronize(
        "garmin",
        since=since,
    )


def write_json(
    activities: List[NormalizedActivity],
    output_path: str,
) -> Path:
    """Enregistre les activités normalisées dans un JSON privé."""
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
            [
                activity.to_dict()
                for activity in activities
            ],
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    return destination


def main() -> None:
    """Lance l'import Garmin."""
    arguments = parse_arguments()

    activities = synchronize(
        arguments.input,
        arguments.since,
    )
    destination = write_json(
        activities,
        arguments.output,
    )

    print(
        f"Import Garmin terminé : "
        f"{len(activities)} activité(s)."
    )
    print(f"Fichier privé : {destination}")

    for activity in activities:
        print(
            f"- {activity.atlas_id} | "
            f"{activity.activity_type} | "
            f"{activity.distance_meters} m | "
            f"{len(activity.samples)} échantillons"
        )


if __name__ == "__main__":
    main()