"""
ATLAS OS
Régénère un programme candidat et prépare sa révision explicable.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.propose_training_program_revision import (  # noqa: E402
    load_program,
    write_json_atomic,
)
from src.training import TrainingProgramRevisionEngine  # noqa: E402

GENERATOR_SCRIPT = (
    PROJECT_ROOT / "scripts" / "generate_training_program.py"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Régénère un candidat depuis le programme actif et "
            "prépare une proposition de révision."
        )
    )
    parser.add_argument(
        "--active",
        default="atlas-data/private/training-program.json",
    )
    parser.add_argument(
        "--candidate",
        default=(
            "atlas-data/private/"
            "training-program-revision-candidate.json"
        ),
    )
    parser.add_argument(
        "--proposal",
        default=(
            "atlas-data/private/"
            "training-program-revision-proposal.json"
        ),
    )
    parser.add_argument("--as-of", default=None)
    return parser.parse_args()


def build_generator_command(
    active: dict,
    candidate_path: str,
) -> list[str]:
    goal = active.get("goal", {})
    settings = active.get("settings", {})

    command = [
        sys.executable,
        "-X",
        "utf8",
        str(GENERATOR_SCRIPT),
        "--goal-name",
        str(goal["name"]),
        "--event-date",
        str(goal["event_date"])[:10],
        "--distance-km",
        str(goal["distance_km"]),
        "--start-date",
        str(active["start_date"])[:10],
        "--running-sessions",
        str(settings["running_sessions_per_week"]),
        "--strength-sessions",
        str(settings["strength_sessions_per_week"]),
        "--preferred-long-run-day",
        str(settings["preferred_long_run_day"]),
        "--recovery-status-available",
        "--output",
        candidate_path,
    ]

    target_time = goal.get("target_time_minutes")
    if target_time is not None:
        command.extend([
            "--target-time-minutes",
            str(target_time),
        ])

    return command


def main() -> None:
    arguments = parse_arguments()
    active = load_program(arguments.active)
    command = build_generator_command(
        active,
        arguments.candidate,
    )
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "Échec de la régénération du programme candidat : "
            + completed.stderr.strip()
        )

    candidate = load_program(arguments.candidate)
    as_of = (
        date.fromisoformat(arguments.as_of)
        if arguments.as_of
        else date.today()
    )
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
    payload["generator_stdout"] = completed.stdout.strip()

    destination = write_json_atomic(
        arguments.proposal,
        payload,
    )

    print("BOUCLE RÉTROACTIVE ATLAS")
    print("=" * 64)
    print("Mémoire FIT + Wellness : actualisée")
    print(f"Programme candidat : {arguments.candidate}")
    print(f"Statut : {proposal.status}")
    print(f"Modifications futures : {len(proposal.changes)}")
    print(
        "Application automatique : non — "
        "validation explicite obligatoire"
    )
    print(f"Proposition privée : {destination}")


if __name__ == "__main__":
    main()