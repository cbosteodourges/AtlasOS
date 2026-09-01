"""Répare uniquement la structure des séances 3+1 déjà présentes.

Les dates déplacées, les décisions utilisateur et les séances supprimées ne sont
jamais recréées. Une sauvegarde est produite avant toute écriture.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.training.training_program_loader import TrainingProgramLoader  # noqa: E402
from src.training.validated_program_activation import (  # noqa: E402
    build_validated_weeks,
)


STRUCTURAL_FIELDS = (
    "workout_type",
    "title",
    "objective",
    "blocks",
    "sport",
    "priority",
    "planned_duration_minutes",
    "planned_distance_km",
    "expected_response",
    "movable",
    "maximum_shift_days",
    "replacement_types",
    "coach_notes",
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audite puis répare la structure des séances du programme 3+1 "
            "sans modifier les dates choisies par l'utilisateur."
        ),
    )
    parser.add_argument(
        "--program",
        default="atlas-data/private/training-program.json",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applique les corrections après l'audit.",
    )
    return parser.parse_args()


def canonical_workouts(program: dict) -> dict[str, dict]:
    weeks = build_validated_weeks(program.get("athlete_snapshot") or {})
    return {
        workout["workout_id"]: workout
        for week in weeks
        for workout in week["workouts"]
    }


def repair(program: dict) -> tuple[dict, list[str]]:
    result = deepcopy(program)
    canonical = canonical_workouts(result)
    changed: list[str] = []

    for week in result.get("weeks") or []:
        for workout in week.get("workouts") or []:
            workout_id = str(workout.get("workout_id") or "")
            reference = canonical.get(workout_id)
            if reference is None:
                continue
            before = {
                field: workout.get(field)
                for field in STRUCTURAL_FIELDS
            }
            for field in STRUCTURAL_FIELDS:
                workout[field] = deepcopy(reference.get(field))
            after = {
                field: workout.get(field)
                for field in STRUCTURAL_FIELDS
            }
            if before != after:
                changed.append(workout_id)

    return result, changed


def main() -> None:
    options = arguments()
    program_path = ROOT / options.program
    with program_path.open("r", encoding="utf-8") as stream:
        program = json.load(stream)

    repaired, changed = repair(program)
    TrainingProgramLoader().from_payload(repaired)

    print(f"Séances contrôlées : {sum(len(w.get('workouts') or []) for w in repaired.get('weeks') or [])}")
    print(f"Séances à corriger : {len(changed)}")
    for workout_id in changed:
        print(f" - {workout_id}")

    if not options.apply:
        print("Audit terminé sans écriture. Relancez avec --apply pour corriger.")
        return

    if not changed:
        print("Programme déjà conforme : aucune écriture nécessaire.")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = program_path.with_name(
        f"{program_path.stem}.backup-before-structure-repair-{stamp}.json"
    )
    shutil.copy2(program_path, backup)

    temporary = program_path.with_suffix(program_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(repaired, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(program_path)

    print("Correction appliquée.")
    print(f"Sauvegarde : {backup.relative_to(ROOT)}")
    print(f"Programme : {program_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
