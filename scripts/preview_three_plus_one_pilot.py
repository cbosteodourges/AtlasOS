"""Génère une comparaison 3+1 sans modifier le programme Atlas actif."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.training.three_plus_one_pilot import (  # noqa: E402
    ThreePlusOnePilotPlanner,
    compare_with_active_program,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prévisualise le protocole Atlas Research 3+1."
    )
    parser.add_argument(
        "--program",
        default="atlas-data/private/training-program.json",
    )
    parser.add_argument("--start-date")
    parser.add_argument(
        "--wellness-status",
        choices=["green", "orange", "red"],
        default="green",
    )
    parser.add_argument(
        "--goal-surface",
        choices=["road", "trail"],
        default="road",
    )
    parser.add_argument("--downhill-experience", action="store_true")
    parser.add_argument(
        "--output",
        default="atlas-data/private/three-plus-one-pilot-preview.json",
    )
    return parser.parse_args()


def next_monday(day: date) -> date:
    days = (7 - day.weekday()) % 7
    return day + timedelta(days=days or 7)


def main() -> None:
    options = arguments()
    source = ROOT / options.program
    with source.open("r", encoding="utf-8") as stream:
        active = json.load(stream)
    start = (
        date.fromisoformat(options.start_date)
        if options.start_date
        else next_monday(date.today())
    )
    pilot = ThreePlusOnePilotPlanner().build(
        start_date=start,
        wellness_status=options.wellness_status,
        goal_surface=options.goal_surface,
        downhill_experience=options.downhill_experience,
    )
    comparison = compare_with_active_program(active, pilot)
    destination = ROOT / options.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as stream:
        json.dump(comparison, stream, ensure_ascii=False, indent=2)
    print("Prévisualisation Atlas Research 3+1 créée.")
    print(f"Programme actif modifié : non")
    print(f"Cycle : {start.isoformat()} → {(start + timedelta(days=27)).isoformat()}")
    try:
        displayed_destination = destination.relative_to(ROOT)
    except ValueError:
        displayed_destination = destination
    print(f"Fichier : {displayed_destination}")


if __name__ == "__main__":
    main()
