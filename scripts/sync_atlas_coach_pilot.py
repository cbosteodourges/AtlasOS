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
from src.performance.cardiac_drift_analyzer import (
    CardiacDriftAnalysis,
    CardiacDriftAnalyzer,
)
from src.performance import (  # noqa: E402
    AthleteProfile,
    DetailedSessionAnalyzer,
    LongitudinalActivityAdapter,
    PhysiologicalReferences,
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
        "--optional-workouts",
        default=(
            "atlas-data/private/atlas-coach-optional-workouts.json"
        ),
        help="Séances ajoutées depuis l'interface Atlas.",
    )
    parser.add_argument(
        "--decisions",
        default=(
            "atlas-data/private/atlas-coach-workout-decisions.json"
        ),
        help="Décisions de séances automatiquement confirmées.",
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
        "--fit-index",
        default=(
            "atlas-data/private/atlas-coach-fit-index.json"
        ),
        help="Index privé des fichiers FIT déjà examinés.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recalcule aussi les activités déjà traitées.",
    )
    return parser.parse_args()


def discover_fit_files(input_directory: str) -> list[Path]:
    """Liste les fichiers FIT sans les décoder."""
    root = Path(input_directory)
    if not root.exists():
        raise FileNotFoundError(f"Dossier Garmin introuvable : {root}")
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".fit"
    )


def fit_file_signature(path: Path) -> str:
    """Construit une signature rapide et stable pour un fichier FIT."""
    stat = path.stat()
    return f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"


def load_fit_index(index_path: str) -> set[str]:
    """Charge les signatures FIT déjà examinées."""
    source = Path(index_path)
    if not source.exists():
        return set()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    values = payload.get("processed_files", []) if isinstance(payload, dict) else []
    return {str(value) for value in values}


def select_fit_files(
    input_directory: str,
    index_path: str,
    output_path: str,
    *,
    force: bool = False,
) -> tuple[list[Path], set[str], bool]:
    """Sélectionne uniquement les FIT nouveaux ou modifiés."""
    files = discover_fit_files(input_directory)
    signatures = load_fit_index(index_path)
    bootstrapped = False

    if not signatures and not force:
        history = Path(output_path)
        if history.exists():
            history_mtime = history.stat().st_mtime_ns
            signatures.update(
                fit_file_signature(path)
                for path in files
                if path.stat().st_mtime_ns <= history_mtime
            )
            bootstrapped = bool(signatures)

    selected = (
        files
        if force
        else [
            path
            for path in files
            if fit_file_signature(path) not in signatures
        ]
    )
    return selected, signatures, bootstrapped


def save_fit_index(index_path: str, signatures: set[str]) -> Path:
    """Enregistre atomiquement l'index incrémental FIT."""
    return write_json_atomic(
        index_path,
        {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "processed_files": sorted(signatures),
        },
    )


def synchronize_garmin(
    input_directory: str,
    fit_paths: list[Path] | None = None,
):
    """Exécute le connecteur Garmin avec une progression visible."""
    def report(path: Path, index: int, total: int) -> None:
        print(f"[{index}/{total}] Analyse Garmin : {path.name}", flush=True)

    registry = ConnectorRegistry()
    registry.register(
        GarminConnector(
            input_directory,
            fit_paths=fit_paths,
            progress_callback=report,
        )
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
    payload: Any,
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


def load_analysis_profile(program_path: str | Path) -> AthleteProfile:
    """Construit le profil utilisé pour classifier les blocs FIT."""

    with Path(program_path).open(
        "r",
        encoding="utf-8",
    ) as input_file:
        program = json.load(input_file)

    snapshot = program.get("athlete_snapshot") or {}
    sv2 = snapshot.get("sv2") or {}

    return AthleteProfile(
        athlete_id=str(snapshot.get("athlete_id") or "atlas-user"),
        declared_level="individualized",
        observed_level="individualized",
        physiological=PhysiologicalReferences(
            age_years=snapshot.get("age_years"),
            sex=snapshot.get("sex"),
            maximum_heart_rate_bpm=snapshot.get(
                "maximum_heart_rate_bpm"
            ),
            resting_heart_rate_bpm=snapshot.get(
                "resting_heart_rate_bpm"
            ),
            threshold_heart_rate_bpm=sv2.get(
                "heart_rate_bpm"
            ),
            vma_kmh=(
                snapshot.get("vma_training_reference_kmh")
                or snapshot.get("vma_kmh")
            ),
            vo2_max=snapshot.get("vo2_max"),
            threshold_speed_kmh=sv2.get("speed_kmh"),
        ),
    )


def load_concatenated_json_lists(path: str | Path):
    """Récupère une ou plusieurs listes JSON accolées dans un même fichier.

    Une écriture interrompue ou concurrente peut laisser deux tableaux JSON
    valides à la suite. Le décodeur standard refuse alors le fichier avec
    ``Extra data``. Atlas fusionne les tableaux et conserve la dernière
    version de chaque séance.
    """
    source = Path(path)
    if not source.exists():
        return []

    content = source.read_text(encoding="utf-8-sig")
    decoder = json.JSONDecoder()
    cursor = 0
    items = []
    document_count = 0
    repair_needed = False

    while cursor < len(content):
        while cursor < len(content) and content[cursor].isspace():
            cursor += 1
        if cursor >= len(content):
            break
        try:
            loaded, cursor = decoder.raw_decode(content, cursor)
        except json.JSONDecodeError:
            if not items:
                raise
            repair_needed = True
            break
        document_count += 1
        if isinstance(loaded, list):
            items.extend(loaded)
        elif isinstance(loaded, dict):
            items.append(loaded)

    by_id = {}
    without_id = []
    for item in items:
        if not isinstance(item, dict):
            continue
        workout_id = str(item.get("workout_id") or "").strip()
        if workout_id:
            by_id[workout_id] = item
        else:
            without_id.append(item)
    merged = [*without_id, *by_id.values()]
    if document_count > 1 or repair_needed:
        backup = source.with_name(
            f"{source.stem}.corrupt-backup-"
            f"{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            f"{source.suffix}"
        )
        backup.write_text(content, encoding="utf-8")
        temporary = source.with_suffix(".json.repair.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as output:
            json.dump(merged, output, ensure_ascii=False, indent=2)
        temporary.replace(source)
    return merged


def load_optional_workouts(path: str | Path, loader):
    """Charge les séances UI en normalisant leurs types vers le moteur."""

    items = load_concatenated_json_lists(path)

    aliases = {
        "endurance_run": "endurance_z2",
        "threshold_run": "threshold_sv2",
        "vo2max_run": "vma_short",
        "double_session": "endurance_z2",
        "double_threshold": "threshold_sv2",
        # L\'interface historique nomme parfois les séances de mobilité
        # « stretching ». Le moteur utilise une famille unique MOBILITY.
        "stretching": "mobility",
    }
    block_aliases = {
        "warmup": "warm_up",
        "interval": "work",
        "cooldown": "cool_down",
        "circuit": "strength",
        "stretching": "mobility",
    }
    normalized = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        workout = dict(raw)
        workout["workout_type"] = aliases.get(
            str(workout.get("workout_type")),
            workout.get("workout_type"),
        )
        workout["blocks"] = [
            {
                **block,
                "block_type": block_aliases.get(
                    str(block.get("block_type")),
                    block.get("block_type"),
                ),
            }
            for block in workout.get("blocks", [])
            if isinstance(block, dict)
        ]
        normalized.append(workout)
    return loader.from_payload({"weeks": [{"workouts": normalized}]})


def detected_optional_threshold_workout(
    longitudinal,
    analysis,
    loader: TrainingProgramLoader,
    profile: AthleteProfile,
):
    """Restaure le 3 x 8 min UI si sa transmission locale a échoué."""

    if str(longitudinal.activity_type).strip().lower() not in {
        "running",
        "run",
        "course",
        "course à pied",
    }:
        return None
    if analysis.dominant_work_type != "sv2":
        return None
    threshold_duration_seconds = sum(
        float(getattr(block, "duration_seconds", 0.0) or 0.0)
        for block in analysis.blocks
        if getattr(block, "block_type", None) == "sv2"
    )
    if not 20 * 60 <= threshold_duration_seconds <= 28 * 60:
        return None

    physiological = profile.physiological
    vma = physiological.vma_kmh
    maximum_hr = physiological.maximum_heart_rate_bpm

    def target(zone, speed_factors, heart_rate_factors, rpe):
        return {
            "zone": zone,
            "speed_min_kmh": (
                round(vma * speed_factors[0], 1)
                if vma is not None else None
            ),
            "speed_max_kmh": (
                round(vma * speed_factors[1], 1)
                if vma is not None else None
            ),
            "heart_rate_min_bpm": (
                round(maximum_hr * heart_rate_factors[0])
                if maximum_hr is not None else None
            ),
            "heart_rate_max_bpm": (
                round(maximum_hr * heart_rate_factors[1])
                if maximum_hr is not None else None
            ),
            "rpe_0_10": rpe,
            "intensity_pattern": (
                "interval" if zone == 4 else "constant"
            ),
        }

    workout_day = longitudinal.start_time.date().isoformat()
    payload = {
        "workout_id": f"{workout_day}-optional-threshold_run",
        "workout_date": workout_day,
        "workout_type": "threshold_sv2",
        "title": "Seuil SV2",
        "objective": (
            "Stimuler le seuil anaérobie avec une charge contrôlée."
        ),
        "sport": "running",
        "priority": "optional",
        "planned_duration_minutes": 55,
        "expected_response": {
            "physiological_load_0_100": 68,
            "biomechanical_load_0_100": 52,
            "recovery_min_hours": 30,
            "recovery_max_hours": 48,
            "sensitive_structures": [
                "mollets",
                "tendons d'Achille",
            ],
        },
        "blocks": [
            {
                "name": "Échauffement",
                "block_type": "warm_up",
                "duration_minutes": 15,
                "target": target(1, (.55, .65), (.62, .71), 2.5),
            },
            {
                "name": "3 × 8 min au SV2",
                "block_type": "work",
                "repetitions": 3,
                "duration_minutes": 8,
                "recovery_minutes": 2,
                "target": target(4, (.86, .92), (.85, .91), 7),
            },
            {
                "name": "Retour au calme",
                "block_type": "cool_down",
                "duration_minutes": 10,
                "target": target(1, (.55, .65), (.62, .71), 2.5),
            },
        ],
        "coach_notes": [
            "Séance facultative restaurée depuis le profil détaillé du FIT.",
            "La récupération écourtée n'empêche pas la validation.",
        ],
    }
    return loader.from_payload({
        "weeks": [{"workouts": [payload]}]
    })[0]


def confirm_matched_workouts(records, decisions_path: str | Path):
    """Valide automatiquement toute séance reliée avec confiance au FIT."""

    destination = Path(decisions_path)
    history = []
    if destination.exists():
        with destination.open("r", encoding="utf-8") as input_file:
            loaded = json.load(input_file)
            if isinstance(loaded, list):
                history = loaded

    existing = {
        (str(item.get("workout_id")), str(item.get("activity_id")))
        for item in history if isinstance(item, dict)
    }
    added = 0
    for record in records:
        match = record.get("atlas_workout_match") or {}
        if not match.get("matched"):
            continue
        key = (str(match.get("workout_id")), str(record.get("activity_id")))
        if not all(key) or key in existing:
            continue
        history.append({
            "decided_at": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "workout_id": key[0],
            "activity_id": key[1],
            "status": "completed",
            "action": "maintain",
            "recalculate_future_program": False,
            "reason": "Séance confirmée automatiquement par le fichier FIT.",
            "explanations": [
                "Le Watcher a importé et analysé l'activité.",
                "La correspondance fiable confirme automatiquement la séance.",
            ],
        })
        existing.add(key)
        added += 1

    if added:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as output:
            json.dump(history, output, ensure_ascii=False, indent=2)
        temporary.replace(destination)
    return added


def persist_restored_optional_workouts(records, output_path: str | Path):
    """Rend au calendrier les séances retrouvées depuis un fichier FIT."""

    restored = [
        item["restored_optional_workout"]
        for item in records
        if isinstance(item.get("restored_optional_workout"), dict)
    ]
    if not restored:
        return 0

    destination = Path(output_path)
    history = []
    if destination.exists():
        history = load_concatenated_json_lists(destination)

    restored_by_id = {
        str(item.get("workout_id")): item
        for item in restored
    }
    history = [
        item for item in history
        if str(item.get("workout_id")) not in restored_by_id
    ]
    history.extend(restored_by_id.values())
    history.sort(key=lambda item: (
        str(item.get("workout_date", "")),
        str(item.get("workout_id", "")),
    ))
    write_json_atomic(str(destination), history)
    return len(restored_by_id)

def build_record(
    normalized_activity,
    workouts,
    loader: TrainingProgramLoader,
    profile: AthleteProfile,
) -> dict[str, Any]:
    """Analyse une activité et cherche sa séance Atlas."""
    longitudinal = LongitudinalActivityAdapter().adapt(
        normalized_activity
    )
    fingerprint = SessionFingerprintBuilder().build(
        longitudinal
    )
    analysis = DetailedSessionAnalyzer().analyze(
        longitudinal,
        profile,
    )

    if not analysis.data_integrity.heart_rate_reliable:
        cardiac_drift = CardiacDriftAnalysis(
            activity_id=longitudinal.atlas_id,
            limitations=[
                "Dérive cardiaque non calculée : fréquence cardiaque jugée non fiable."
            ],
        )
    elif analysis.session_type not in {"recovery", "endurance", "long_run"}:
        cardiac_drift = CardiacDriftAnalysis(
            activity_id=longitudinal.atlas_id,
            limitations=[
                "Dérive cardiaque non calculée sur une séance intermittente ou intense."
            ],
        )
    else:
        cardiac_drift = CardiacDriftAnalyzer().analyze(
            longitudinal
        )

    candidates = loader.candidates_for_activity(
        workouts,
        activity_date=longitudinal.start_time.date(),
        sport=fingerprint.sport,
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

    restored = None
    if best_match is None or not best_match.matched:
        restored = detected_optional_threshold_workout(
            longitudinal,
            analysis,
            loader,
            profile,
        )
        if restored is not None:
            restored_match = AtlasWorkoutExecutionMatcher().match(
                restored,
                longitudinal,
                analysis,
            )
            if (
                best_match is None
                or restored_match.match_confidence_score
                > best_match.match_confidence_score
            ):
                best_match = restored_match

    return {
        "activity_id": longitudinal.atlas_id,
        "provider": normalized_activity.provider,
        "external_id": normalized_activity.external_id,
        "start_time": longitudinal.start_time,
        "processed_at": datetime.now(timezone.utc),
        "fingerprint": asdict(fingerprint),
        "detailed_analysis": asdict(analysis),
        "cardiac_drift": asdict(cardiac_drift),
        "atlas_workout_match": (
            best_match.to_dict()
            if best_match is not None
            else None
        ),
        "automatic_learning_allowed": bool(
            best_match is not None
            and best_match.matched
        ),
        "restored_optional_workout": (
            restored.to_dict()
            if restored is not None
            and best_match is not None
            and best_match.workout_id == restored.workout_id
            else None
        ),
    }


def main() -> None:
    """Lance une synchronisation pilote complète."""
    arguments = parse_arguments()
    loader = TrainingProgramLoader()
    workouts = loader.load(arguments.program)
    workouts.extend(
        load_optional_workouts(arguments.optional_workouts, loader)
    )
    profile = load_analysis_profile(arguments.program)
    history = load_history(arguments.output)
    fit_paths, fit_signatures, bootstrapped = select_fit_files(
        arguments.input,
        arguments.fit_index,
        arguments.output,
        force=arguments.force,
    )
    total_fit_files = len(discover_fit_files(arguments.input))
    if bootstrapped:
        print(
            "Index FIT initialisé depuis l'historique existant : "
            f"{len(fit_signatures)} fichier(s) déjà traité(s)."
        )
    print(
        f"Fichiers FIT à analyser : {len(fit_paths)}/"
        f"{total_fit_files}.",
        flush=True,
    )
    activities = (
        synchronize_garmin(arguments.input, fit_paths)
        if fit_paths
        else []
    )

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
            profile,
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
    fit_signatures.update(
        fit_file_signature(path)
        for path in fit_paths
    )
    fit_index = save_fit_index(
        arguments.fit_index,
        fit_signatures,
    )
    persist_restored_optional_workouts(
        new_records,
        arguments.optional_workouts,
    )
    confirmed_count = confirm_matched_workouts(
        new_records,
        arguments.decisions,
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
    print(
        f"Séances confirmées automatiquement : {confirmed_count}."
    )
    for record in new_records:
        match = record.get("atlas_workout_match") or {}
        execution = match.get("execution") or {}
        state = "associée" if match.get("matched") else "non associée"
        print(
            "- "
            f"{str(record.get('start_time') or '')[:16]} | "
            f"{execution.get('workout_name') or 'aucune séance'} | "
            f"{state} ({match.get('match_confidence_score') or 0}/100) | "
            f"{match.get('workout_id') or 'sans identifiant'}"
        )
    print(f"Historique privé : {destination}")
    print(f"Index FIT : {fit_index}")


if __name__ == "__main__":
    main()
