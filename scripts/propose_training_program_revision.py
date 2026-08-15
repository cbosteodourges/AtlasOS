"""
ATLAS OS
Crée une proposition explicable de révision du programme.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.training import (  # noqa: E402
    TrainingProgramRevisionEngine,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare le programme actif à un candidat régénéré "
            "sans appliquer automatiquement les modifications."
        )
    )
    parser.add_argument(
        "--active",
        default="atlas-data/private/training-program.json",
        help="Programme actuellement validé.",
    )
    parser.add_argument(
        "--candidate",
        default=(
            "atlas-data/private/"
            "training-program-revision-candidate.json"
        ),
        help="Programme candidat régénéré.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "training-program-revision-proposal.json"
        ),
        help="Proposition de révision à enregistrer.",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="Date ISO séparant les séances passées et futures.",
    )
    return parser.parse_args()


def load_program(path: str) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(
            f"Programme Atlas introuvable : {source}"
        )

    with source.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    if not isinstance(payload, dict):
        raise ValueError(
            f"Le programme Atlas doit être un objet JSON : {source}"
        )
    return payload


def write_json_atomic(
    path: str,
    payload: dict[str, Any],
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    with temporary.open("w", encoding="utf-8") as output_file:
        json.dump(
            payload,
            output_file,
            ensure_ascii=False,
            indent=2,
        )
        output_file.write("\n")

    temporary.replace(destination)
    return destination


def main() -> None:
    arguments = parse_arguments()
    as_of = (
        date.fromisoformat(arguments.as_of)
        if arguments.as_of
        else date.today()
    )
    active = load_program(arguments.active)
    candidate = load_program(arguments.candidate)
    proposal = TrainingProgramRevisionEngine().compare(
        active,
        candidate,
        as_of=as_of,
    )
    payload = proposal.to_dict()
    payload["generated_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    payload["active_program"] = arguments.active
    payload["candidate_program"] = arguments.candidate

    destination = write_json_atomic(
        arguments.output,
        payload,
    )

    print("PROPOSITION DE RÉVISION ATLAS")
    print("=" * 64)
    print(f"Statut : {proposal.status}")
    print(f"Modifications futures : {len(proposal.changes)}")
    print(
        "Validation requise : "
        f"{'oui' if proposal.requires_approval else 'non'}"
    )
    print(f"Proposition privée : {destination}")


if __name__ == "__main__":
    main()