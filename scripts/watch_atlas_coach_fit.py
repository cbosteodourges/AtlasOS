"""
ATLAS OS
Surveillance automatique des nouveaux fichiers Garmin FIT.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "sync_atlas_coach_pilot.py"
)
LOG_FILE = (
    PROJECT_ROOT
    / "atlas-data"
    / "private"
    / "atlas-coach-watcher.log"
)


def parse_arguments() -> argparse.Namespace:
    """Lit les options de surveillance."""
    parser = argparse.ArgumentParser(
        description=(
            "Surveille l'arrivée de fichiers FIT et lance "
            "automatiquement Atlas Coach."
        )
    )
    parser.add_argument(
        "--input",
        default="atlas-data/garmin",
        help="Dossier surveillé.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Intervalle de contrôle en secondes.",
    )
    return parser.parse_args()


def write_log(message: str) -> None:
    """Écrit un événement dans le journal privé."""
    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
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

    print(line, flush=True)


def fit_snapshot(directory: Path) -> dict[Path, tuple[int, int]]:
    """Retourne la taille et la date de chaque fichier FIT."""
    if not directory.exists():
        return {}

    return {
        path.resolve(): (
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".fit"
    }


def run_sync(
    fit_path: Path,
) -> subprocess.CompletedProcess[str]:
    """Analyse uniquement le nouveau fichier FIT."""
    with TemporaryDirectory(
        prefix="atlas-coach-fit-"
    ) as temporary_directory:
        temporary_path = Path(temporary_directory)
        copied_fit = temporary_path / fit_path.name
        shutil.copy2(fit_path, copied_fit)

        command = [
            sys.executable,
            "-X",
            "utf8",
            str(SYNC_SCRIPT),
            "--input",
            str(temporary_path),
        ]
        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

def notify_windows(title: str, message: str) -> None:
    """Affiche une notification locale sous Windows."""
    safe_title = title.replace("'", "''")
    safe_message = message.replace("'", "''")

    powershell_script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$notification = New-Object "
        "System.Windows.Forms.NotifyIcon;"
        "$notification.Icon = "
        "[System.Drawing.SystemIcons]::Information;"
        "$notification.BalloonTipTitle = "
        f"'{safe_title}';"
        "$notification.BalloonTipText = "
        f"'{safe_message}';"
        "$notification.Visible = $true;"
        "$notification.ShowBalloonTip(8000);"
        "Start-Sleep -Seconds 9;"
        "$notification.Dispose();"
    )

    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-Command",
            powershell_script,
        ],
        cwd=PROJECT_ROOT,
    )


def imported_count(output: str) -> int:
    """Extrait le nombre d'activités importées."""
    match = re.search(
        r"(\d+)\s+nouvelle\(s\)\s+activité",
        output,
    )
    return int(match.group(1)) if match else 0


def wait_until_stable(
    path: Path,
    interval: float,
    attempts: int = 3,
) -> bool:
    """Attend que la copie du fichier FIT soit terminée."""
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


def main() -> None:
    """Surveille continuellement les fichiers Garmin."""
    arguments = parse_arguments()
    input_directory = (
        PROJECT_ROOT / arguments.input
    ).resolve()
    input_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_log("Surveillance automatique Atlas Coach active.")
    write_log(f"Dossier FIT : {input_directory}")

    known = fit_snapshot(input_directory)

    try:
        while True:
            time.sleep(arguments.interval)
            current = fit_snapshot(input_directory)

            changed = [
                path
                for path, signature in current.items()
                if known.get(path) != signature
            ]

            for path in changed:
                write_log(
                    f"Nouveau fichier détecté : {path.name}"
                )

                if not wait_until_stable(
                    path,
                    arguments.interval,
                ):
                    write_log(
                        "Fichier encore incomplet ; "
                        "il sera vérifié de nouveau."
                    )
                    continue

                completed = run_sync(path)

                if completed.stdout.strip():
                    write_log(completed.stdout.strip())

                if completed.stderr.strip():
                    write_log(completed.stderr.strip())

                if completed.returncode != 0:
                    write_log(
                        "Échec de la synchronisation "
                        f"(code {completed.returncode})."
                    )
                    notify_windows(
                        "Atlas Coach",
                        "Échec de l'import Garmin. "
                        "Consultez le journal Atlas.",
                    )
                    continue

                count = imported_count(completed.stdout)

                if count > 0:
                    write_log(
                        f"{count} activité(s) importée(s) "
                        "et analysée(s)."
                    )
                    notify_windows(
                        "Atlas Coach",
                        f"{count} nouvelle activité Garmin "
                        "a été importée et analysée.",
                    )
                else:
                    write_log(
                        "Aucune nouvelle activité à importer."
                    )

            known = fit_snapshot(input_directory)

    except KeyboardInterrupt:
        write_log("Surveillance Atlas Coach arrêtée.")


if __name__ == "__main__":
    main()