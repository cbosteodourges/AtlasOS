"""
ATLAS OS
Surveillance automatique des archives Garmin Wellness.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from watch_atlas_coach_fit import notify_windows


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUSION_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "analyze_training_history_fusion.py"
)
LOG_FILE = (
    PROJECT_ROOT
    / "atlas-data"
    / "private"
    / "atlas-wellness-watcher.log"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Surveille les archives Garmin Wellness et actualise "
            "automatiquement la mémoire physiologique Atlas."
        )
    )
    parser.add_argument(
        "--input",
        default="atlas-data/garmin/wellness-archives",
        help="Dossier contenant les ZIP Wellness quotidiens.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="Intervalle de surveillance en secondes.",
    )
    return parser.parse_args()


def write_log(message: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    line = f"{timestamp} | {message}"

    with LOG_FILE.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as log_file:
        log_file.write(line + "\n")


def archive_snapshot(
    directory: Path,
) -> dict[Path, tuple[int, int]]:
    if not directory.exists():
        return {}

    return {
        path.resolve(): (
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in directory.glob("*.zip")
        if path.is_file()
    }


def wait_until_stable(
    path: Path,
    interval: float,
    attempts: int = 3,
) -> bool:
    previous_size: int | None = None
    stable_count = 0

    for _ in range(max(6, attempts * 4)):
        if not path.exists():
            return False

        current_size = path.stat().st_size

        if current_size > 0 and current_size == previous_size:
            stable_count += 1
            if stable_count >= attempts:
                return True
        else:
            stable_count = 0

        previous_size = current_size
        time.sleep(interval)

    return False


def run_fusion() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(FUSION_SCRIPT),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


def main() -> None:
    arguments = parse_arguments()
    input_directory = (
        PROJECT_ROOT / arguments.input
    ).resolve()
    input_directory.mkdir(parents=True, exist_ok=True)

    known = archive_snapshot(input_directory)
    write_log(
        "Surveillance Wellness active : "
        f"{len(known)} archive(s) connue(s)."
    )

    try:
        while True:
            time.sleep(arguments.interval)
            current = archive_snapshot(input_directory)
            changed = [
                path
                for path, signature in current.items()
                if known.get(path) != signature
            ]

            if not changed:
                known = current
                continue

            stable_archives = [
                path
                for path in changed
                if wait_until_stable(
                    path,
                    min(arguments.interval, 2.0),
                )
            ]

            if not stable_archives:
                known = archive_snapshot(input_directory)
                continue

            names = ", ".join(
                path.name for path in stable_archives
            )
            write_log(f"Nouvelle archive détectée : {names}")

            completed = run_fusion()

            if completed.returncode != 0:
                write_log(
                    "Échec de la fusion Wellness : "
                    f"{completed.stderr.strip()}"
                )
                notify_windows(
                    "Atlas Wellness",
                    "Échec de la mise à jour physiologique.",
                )
            else:
                write_log(
                    "Fusion FIT + Wellness actualisée avec succès."
                )
                notify_windows(
                    "Atlas Wellness",
                    (
                        f"{len(stable_archives)} nouvelle(s) journée(s) "
                        "Wellness intégrée(s)."
                    ),
                )

            known = archive_snapshot(input_directory)

    except KeyboardInterrupt:
        write_log("Surveillance Wellness arrêtée.")


if __name__ == "__main__":
    main()