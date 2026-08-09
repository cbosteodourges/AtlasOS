"""
ATLAS OS
Synchronisation pilote Garmin vers Atlas Coach.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors import (  # noqa: E402
    ActivitySyncService,
    ConnectorRegistry,
    GarminConnector,
)
from src.performance import (  # noqa: E402
    DetailedSessionAnalyzer,
    LongitudinalActivityAdapter,
    SessionFingerprintBuilder,
)
from src.training import (  # noqa: E402
    AtlasWorkoutExecutionMatcher,
    TrainingProgramLoader,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de synchronisation."""
    parser = argparse.ArgumentParser(
        description=(
            "Importe les nouvelles activités Garmin, "
            "les analyse et les rapproche du programme Atlas."
        )
    )
    parser.add_argument(
        "--input",
        default="atlas-data/garmin",
        help="Dossier contenant les fichiers FIT.",
    )
    parser.add_argument(
        "--program",
        default=(
            "atlas-data/private/training-program.json"
        ),
        help="Programme Atlas Coach exporté.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "atlas-coach-executions.json"
        ),
        help="Historique privé des activités analysées.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recalcule aussi les activités déjà traitées.",
    )
    return parser.parse_args()


def synchronize_garmin(
    input_directory: str,
):
    """Exécute le connecteur Garmin existant."""
    registry = ConnectorRegistry()
    registry.register(
        GarminConnector(input_directory)
    )
    return ActivitySyncService(
        registry
    ).synchronize("garmin")


def load_history(
    output_path: str,
) -> list[dict[str, Any]]:
    """Charge l'historique déjà traité."""
    source = Path(output_path)
    if not source.exists():
        return []

    with source.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    if not isinstance(payload, list):
        raise ValueError(
            "L'historique Atlas Coach doit être une liste."
        )
    return payload


def write_json_atomic(
    output_path: str,
    payload: list[dict[str, Any]],
) -> Path:
    """Écrit le JSON sans risquer un fichier partiel."""
    destination = Path(output_path)
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
            default=json_default,
        )

    temporary.replace(destination)
    return destination


def json_default(value: Any) -> Any:
    """Sérialise les types Atlas courants."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(
        f"Type non sérialisable : {type(value).__name__}"
    )


def build_record(
    normalized_activity,
    workouts,
    loader: TrainingProgramLoader,
) -> dict[str, Any]:
    """Analyse une activité et cherche sa séance Atlas."""
    longitudinal = LongitudinalActivityAdapter().adapt(
        normalized_activity
    )
    fingerprint = SessionFingerprintBuilder().build(
        longitudinal
    )
    analysis = DetailedSessionAnalyzer().analyze(
        longitudinal
    )

    candidates = loader.candidates_for_activity(
        workouts,
        activity_date=longitudinal.start_time.date(),
        sport=longitudinal.activity_type,
    )

    matches = [
        AtlasWorkoutExecutionMatcher().match(
            candidate,
            longitudinal,
            analysis,
        )
        for candidate in candidates
    ]
    best_match = (
        max(
            matches,
            key=lambda item: (
                item.match_confidence_score,
                item.execution.execution_score,
            ),
        )
        if matches
        else None
    )

    return {
        "activity_id": longitudinal.atlas_id,
        "provider": normalized_activity.provider,
        "external_id": normalized_activity.external_id,
        "start_time": longitudinal.start_time,
        "processed_at": datetime.now(timezone.utc),
        "fingerprint": asdict(fingerprint),
        "detailed_analysis": asdict(analysis),
        "atlas_workout_match": (
            best_match.to_dict()
            if best_match is not None
            else None
        ),
        "automatic_learning_allowed": bool(
            best_match is not None
            and best_match.matched
        ),
    }


def main() -> None:
    """Lance une synchronisation pilote complète."""
    arguments = parse_arguments()
    loader = TrainingProgramLoader()
    workouts = loader.load(arguments.program)
    activities = synchronize_garmin(arguments.input)
    history = load_history(arguments.output)

    known_ids = {
        str(item.get("activity_id"))
        for item in history
    }
    new_records = []

    for activity in activities:
        if (
            not arguments.force
            and activity.atlas_id in known_ids
        ):
            continue

        record = build_record(
            activity,
            workouts,
            loader,
        )

        if arguments.force:
            history = [
                item
                for item in history
                if item.get("activity_id")
                != activity.atlas_id
            ]

        history.append(record)
        new_records.append(record)

    history.sort(
        key=lambda item: str(item.get("start_time", ""))
    )
    destination = write_json_atomic(
        arguments.output,
        history,
    )

    matched_count = sum(
        1
        for item in new_records
        if item["automatic_learning_allowed"]
    )

    print(
        f"Synchronisation Atlas Coach terminée : "
        f"{len(new_records)} nouvelle(s) activité(s)."
    )
    print(
        f"Correspondances Atlas fiables : "
        f"{matched_count}/{len(new_records)}."
    )
    print(f"Historique privé : {destination}")


if __name__ == "__main__":
    main()