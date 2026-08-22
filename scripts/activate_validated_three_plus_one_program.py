"""Active localement le programme 3+1 explicitement validé."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.training.training_program_loader import TrainingProgramLoader  # noqa: E402
from src.training.validated_program_activation import activate_program  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Active le programme 3+1 validé jusqu'à l'échéance."
    )
    parser.add_argument(
        "--program",
        default="atlas-data/private/training-program.json",
    )
    parser.add_argument(
        "--confirm-activation",
        action="store_true",
        help="Confirmation explicite requise pour remplacer le programme actif.",
    )
    return parser.parse_args()


def main() -> None:
    options = arguments()
    if not options.confirm_activation:
        raise SystemExit(
            "Activation annulée : ajoutez --confirm-activation après validation utilisateur."
        )
    destination = ROOT / options.program
    if not destination.is_file():
        raise FileNotFoundError(f"Programme actif introuvable : {destination}")

    with destination.open("r", encoding="utf-8") as stream:
        active = json.load(stream)
    activated = activate_program(active)

    # Validation complète du schéma avant toute écriture.
    workouts = TrainingProgramLoader().from_payload(activated)
    if not workouts:
        raise ValueError("Le programme activé ne contient aucune séance.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = destination.with_name(
        f"{destination.stem}.backup-before-3plus1-{stamp}{destination.suffix}"
    )
    shutil.copy2(destination, backup)

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(activated, stream, ensure_ascii=False, indent=2)
    temporary.replace(destination)

    running = sum(
        item.get("sport") == "running"
        for week in activated["weeks"]
        for item in week["workouts"]
    )
    print("Programme Norwegian Singles 3+1 activé.")
    print("Validation utilisateur : confirmée")
    print(f"Cycle : {activated['start_date']} → {activated['end_date']}")
    print(f"Semaines : {len(activated['weeks'])}")
    print(f"Séances course : {running}")
    print(f"Sauvegarde : {backup.relative_to(ROOT)}")
    print(f"Programme actif : {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
