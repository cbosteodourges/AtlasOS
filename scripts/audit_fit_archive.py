"""Inventorie et chronomètre une archive privée d'activités Garmin FIT."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors import GarminConnector  # noqa: E402


PHYSIOLOGY_TOKENS = (
    "vo2",
    "vo_2",
    "fitness",
    "threshold",
    "training_effect",
    "anaerobic",
    "stamina",
    "performance_condition",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audite tous les FIT d'un dossier sans modifier les données sources."
    )
    parser.add_argument(
        "--input",
        default="atlas-data/garmin",
        help="Dossier racine contenant les fichiers FIT Garmin.",
    )
    parser.add_argument(
        "--output",
        default="atlas-data/private/fit-archive-audit.json",
        help="Rapport JSON privé généré par l'audit.",
    )
    return parser.parse_args()


def discover_fit_files(input_directory: str | Path) -> list[Path]:
    root = Path(input_directory)
    if not root.exists():
        raise FileNotFoundError(f"Dossier FIT introuvable : {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Le chemin FIT n'est pas un dossier : {root}")
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".fit"
    )


def safe_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [safe_value(item) for item in value[:10]]
    return str(value)


def physiology_fields(messages: dict[str, Any]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for message_name, records in messages.items():
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            for field, value in record.items():
                field_name = str(field).lower()
                if not any(token in field_name for token in PHYSIOLOGY_TOKENS):
                    continue
                key = f"{message_name}.{field}"
                entry = found.setdefault(key, {"occurrences": 0, "examples": []})
                entry["occurrences"] += 1
                example = safe_value(value)
                if example not in entry["examples"] and len(entry["examples"]) < 12:
                    entry["examples"].append(example)
    return found


def audit_archive(
    input_directory: str | Path,
    decoder: Callable[[Path], tuple[dict[str, Any], list[Any]]] | None = None,
) -> dict[str, Any]:
    paths = discover_fit_files(input_directory)
    decode = decoder or GarminConnector._decode
    started = perf_counter()
    total_bytes = sum(path.stat().st_size for path in paths)
    message_counts: Counter[str] = Counter()
    sport_counts: Counter[str] = Counter()
    field_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"files": 0, "occurrences": 0, "examples": []}
    )
    audited_files = []
    activity_days = []
    error_count = 0

    for index, path in enumerate(paths, start=1):
        file_started = perf_counter()
        record: dict[str, Any] = {
            "path": str(path.relative_to(Path(input_directory))),
            "size_bytes": path.stat().st_size,
        }
        try:
            messages, errors = decode(path)
            if errors:
                raise ValueError(str(errors))
            counts = {
                name: len(items)
                for name, items in messages.items()
                if isinstance(items, list)
            }
            message_counts.update(counts)
            sessions = messages.get("session_mesgs", [])
            session = sessions[0] if sessions and isinstance(sessions[0], dict) else {}
            sport = str(session.get("sport") or "unknown")
            sport_counts[sport] += 1
            started_at = safe_value(session.get("start_time"))
            if started_at:
                activity_days.append(str(started_at)[:10])
            candidates = physiology_fields(messages)
            for field, details in candidates.items():
                aggregate = field_totals[field]
                aggregate["files"] += 1
                aggregate["occurrences"] += details["occurrences"]
                for example in details["examples"]:
                    if example not in aggregate["examples"] and len(aggregate["examples"]) < 12:
                        aggregate["examples"].append(example)
            record.update({
                "status": "ok",
                "sport": sport,
                "start_time": started_at,
                "message_count": sum(counts.values()),
                "physiology_fields": sorted(candidates),
            })
        except Exception as error:  # rapporter un FIT illisible sans arrêter le lot
            error_count += 1
            record.update({"status": "error", "error": str(error)})
        record["elapsed_seconds"] = round(perf_counter() - file_started, 4)
        audited_files.append(record)
        print(f"[{index}/{len(paths)}] {path.name} · {record['status']}", flush=True)

    elapsed = perf_counter() - started
    return {
        "schema": "atlas_fit_archive_audit_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(Path(input_directory).resolve()),
        "file_count": len(paths),
        "decoded_file_count": len(paths) - error_count,
        "error_count": error_count,
        "total_size_bytes": total_bytes,
        "elapsed_seconds": round(elapsed, 3),
        "files_per_second": round(len(paths) / max(elapsed, .001), 2),
        "megabytes_per_second": round(total_bytes / 1_000_000 / max(elapsed, .001), 2),
        "first_activity_day": min(activity_days) if activity_days else None,
        "last_activity_day": max(activity_days) if activity_days else None,
        "sports": dict(sport_counts.most_common()),
        "message_types": dict(message_counts.most_common()),
        "physiology_fields": dict(sorted(field_totals.items())),
        "files": audited_files,
    }


def main() -> None:
    arguments = parse_arguments()
    report = audit_archive(arguments.input)
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"Audit terminé : {report['decoded_file_count']}/{report['file_count']} FIT décodés "
        f"en {report['elapsed_seconds']:.2f} s · {report['files_per_second']:.1f} fichier(s)/s."
    )
    print(f"Champs physiologiques détectés : {len(report['physiology_fields'])}.")
    print(f"Rapport privé : {destination}")


if __name__ == "__main__":
    main()
