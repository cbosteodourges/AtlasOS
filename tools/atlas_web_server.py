"""
ATLAS OS — serveur web local avec passerelle Atlas Brain.
"""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.atlas_brain import AtlasBrain
from src.connectors.garmin_wellness import GarminWellnessConnector
from src.patient.patient import Patient
from src.twin.digital_twin import DigitalTwin
from src.training.daily_preparation_service import (
    DailyPreparationService,
)
from src.training.training_program_loader import TrainingProgramLoader
from src.training.user_workout_decision import UserWorkoutDecisionEngine


def calculate_age(birth_date):
    if not birth_date:
        return 0

    try:
        born = date.fromisoformat(str(birth_date)[:10])
        today = date.today()

        return (
            today.year
            - born.year
            - ((today.month, today.day) < (born.month, born.day))
        )
    except (TypeError, ValueError):
        return 0


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def serialize(value):
    if is_dataclass(value):
        return asdict(value)

    if hasattr(value, "__dict__"):
        return value.__dict__

    return str(value)


PROGRAM_PATH = ROOT / "atlas-data" / "private" / "training-program.json"
WORKOUT_DECISIONS_PATH = (
    ROOT
    / "atlas-data"
    / "private"
    / "atlas-coach-workout-decisions.json"
)


EXECUTIONS_PATH = (
    ROOT
    / "atlas-data"
    / "private"
    / "atlas-coach-executions.json"
)

WORKOUT_CONTEXTS_PATH = (
    ROOT
    / "atlas-data"
    / "private"
    / "atlas-coach-workout-contexts.json"
)

OPTIONAL_WORKOUTS_PATH = (
    ROOT
    / "atlas-data"
    / "private"
    / "atlas-coach-optional-workouts.json"
)


def record_optional_workout(payload):
    """Persiste une séance ajoutée dans l'interface pour le Watcher."""

    workout_id = str(payload.get("workout_id") or "").strip()
    workout_date = str(payload.get("workout_date") or "").strip()
    deleting = bool(payload.get("delete"))
    if not workout_id or (not deleting and not workout_date):
        raise ValueError("Séance facultative incomplète.")

    if not deleting:
        date.fromisoformat(workout_date)
    history = []
    if OPTIONAL_WORKOUTS_PATH.exists():
        with OPTIONAL_WORKOUTS_PATH.open("r", encoding="utf-8") as source:
            loaded = json.load(source)
            if isinstance(loaded, list):
                history = loaded

    history = [
        item for item in history
        if str(item.get("workout_id") or "") != workout_id
    ]
    if not deleting:
        history.append(payload)
    OPTIONAL_WORKOUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OPTIONAL_WORKOUTS_PATH.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(history, output, ensure_ascii=False, indent=2)
    temporary.replace(OPTIONAL_WORKOUTS_PATH)
    return {"workout_id": workout_id, "deleted": deleting, **payload}

def selected_fields(value, field_names):
    """Copie uniquement les champs explicitement autorisés."""

    if not isinstance(value, dict):
        return {}

    return {
        field: value.get(field)
        for field in field_names
        if field in value
    }


def execution_summary(item):
    """Construit un compte-rendu navigateur sans exposer le fichier privé."""

    if not isinstance(item, dict):
        return None

    match = item.get("atlas_workout_match") or {}
    execution = match.get("execution") or {}
    drift = item.get("cardiac_drift") or {}
    analysis = item.get("detailed_analysis") or {}
    integrity = analysis.get("data_integrity") or {}
    fingerprint = item.get("fingerprint") or {}

    return {
        "activity_id": item.get("activity_id"),
        "provider": item.get("provider"),
        "start_time": item.get("start_time"),
        "processed_at": item.get("processed_at"),
        "automatic_learning_allowed": item.get(
            "automatic_learning_allowed"
        ),
        "workout_match": {
            **selected_fields(
                match,
                (
                    "workout_id",
                    "matched",
                    "match_confidence_score",
                    "date_difference_days",
                    "duration_compliance_score",
                    "distance_compliance_score",
                    "target_compliance_score",
                    "physiological_load_score",
                    "biomechanical_load_score",
                    "reasons",
                ),
            ),
            "execution": selected_fields(
                execution,
                (
                    "workout_name",
                    "workout_origin",
                    "origin_confidence_score",
                    "origin_reasons",
                    "execution_score",
                    "target_compliance_score",
                    "planned_step_count",
                    "executed_block_count",
                    "planned_repetition_count",
                    "completed_repetition_count",
                    "observations",
                ),
            ),
        },
        "cardiac_drift": {
            **selected_fields(
                drift,
                (
                    "analyzable",
                    "aerobic_decoupling_percent",
                    "confidence_score",
                    "drift_classification",
                    "heart_rate_change_bpm",
                    "speed_change_percent",
                    "warmup_excluded_minutes",
                    "valid_sample_count",
                    "excluded_hill_sample_count",
                    "interpretation",
                    "limitations",
                    "planning_influences",
                ),
            ),
            "first_segment": selected_fields(
                drift.get("first_segment"),
                (
                    "average_heart_rate_bpm",
                    "average_speed_kmh",
                    "average_temperature_c",
                    "duration_minutes",
                    "sample_count",
                ),
            ),
            "second_segment": selected_fields(
                drift.get("second_segment"),
                (
                    "average_heart_rate_bpm",
                    "average_speed_kmh",
                    "average_temperature_c",
                    "duration_minutes",
                    "sample_count",
                ),
            ),
        },
        "analysis": {
            **selected_fields(
                analysis,
                (
                    "analysis_confidence_score",
                    "dominant_work_type",
                    "physiological_load_score",
                    "biomechanical_load_score",
                    "work_duration_seconds",
                    "work_distance_meters",
                    "recovery_duration_seconds",
                    "recovery_distance_meters",
                    "interpretation",
                    "planning_influences",
                    "threshold_observations",
                    "blocks",
                ),
            ),
            "data_integrity": selected_fields(
                integrity,
                (
                    "sensor_quality_score",
                    "identity_confidence_score",
                    "heart_rate_reliable",
                    "physiological_data_usable",
                    "recommended_action",
                    "warnings",
                    "anomalies",
                ),
            ),
        },
        "activity": selected_fields(
            fingerprint,
            (
                "sport",
                "session_type",
                "distance_km",
                "duration_minutes",
                "pace_seconds_per_km",
                "average_speed_kmh",
                "average_heart_rate_bpm",
                "maximum_heart_rate_bpm",
                "elevation_gain_m",
                "temperature_c",
                "training_load",
                "data_quality_score",
                "fingerprint_confidence_score",
                "perceived_effort_1_to_10",
                "feeling_score_0_to_100",
                "aerobic_training_effect",
                "anaerobic_training_effect",
                "classification_reasons",
                "missing_data",
            ),
        ),
    }


def load_execution_summaries():
    """Charge les comptes-rendus synthétiques du plus récent au plus ancien."""

    if not EXECUTIONS_PATH.exists():
        return []

    with EXECUTIONS_PATH.open("r", encoding="utf-8") as source:
        data = json.load(source)

    items = data if isinstance(data, list) else [data]
    summaries = [
        summary
        for summary in (execution_summary(item) for item in items)
        if summary is not None
    ]

    return sorted(
        summaries,
        key=lambda item: str(item.get("start_time") or ""),
        reverse=True,
    )

def load_workout_contexts():
    """Charge l’historique des contextes déclarés."""

    if not WORKOUT_CONTEXTS_PATH.exists():
        return []

    with WORKOUT_CONTEXTS_PATH.open("r", encoding="utf-8") as source:
        loaded = json.load(source)

    return loaded if isinstance(loaded, list) else []


def latest_workout_context(workout_id):
    """Retourne la déclaration la plus récente d’une séance."""

    matches = [
        item
        for item in load_workout_contexts()
        if str(item.get("workout_id") or "") == workout_id
    ]

    return matches[-1] if matches else None


def context_score(value, field_name):
    """Valide une échelle utilisateur comprise entre 0 et 10."""

    if value in (None, ""):
        return None

    try:
        score = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{field_name} doit être compris entre 0 et 10."
        ) from error

    if not 0 <= score <= 10:
        raise ValueError(
            f"{field_name} doit être compris entre 0 et 10."
        )

    return score


def record_workout_context(payload):
    """Enregistre le contexte déclaré sans modifier les données Garmin."""

    workout_id = str(payload.get("workout_id") or "").strip()
    activity_id = str(payload.get("activity_id") or "").strip()
    comment = str(payload.get("comment") or "").strip()

    if not workout_id:
        raise ValueError("workout_id est obligatoire.")
    if len(comment) > 1200:
        raise ValueError(
            "Le commentaire ne peut pas dépasser 1200 caractères."
        )

    else:
        impact = {
            "workout_id": workout.workout_id,
            "status": "planned",
            "action": "restore",
            "recalculate_future_program": False,
            "removed_duration_minutes": 0,
            "removed_physiological_load": 0,
            "removed_biomechanical_load": 0,
            "shift_days": 0,
            "reason": reason or "Decision modifiee par l'utilisateur",
            "explanations": [
                "La seance est reactivee dans le programme.",
            ],
        }
    record = {
        "workout_id": workout_id,
        "activity_id": activity_id or None,
        "heat": bool(payload.get("heat")),
        "relief": bool(payload.get("relief")),
        "pain_0_to_10": context_score(
            payload.get("pain_0_to_10"),
            "La douleur",
        ),
        "fatigue_0_to_10": context_score(
            payload.get("fatigue_0_to_10"),
            "La fatigue",
        ),
        "comment": comment,
        "recorded_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
    }

    history = load_workout_contexts()
    history.append(record)
    WORKOUT_CONTEXTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = WORKOUT_CONTEXTS_PATH.with_suffix(".tmp")

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            history,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    temporary.replace(WORKOUT_CONTEXTS_PATH)
    return record

def record_workout_decision(payload):
    """Enregistre et analyse une décision prise sur une séance."""

    workout_id = str(payload.get("workout_id") or "").strip()
    status = str(payload.get("status") or "").strip().lower()
    reason = str(payload.get("reason") or "").strip()

    if not workout_id:
        raise ValueError("workout_id est obligatoire.")
    if status not in {"completed", "skipped", "planned"}:
        raise ValueError("Statut de séance non pris en charge.")

    workouts = TrainingProgramLoader().load(PROGRAM_PATH)
    workout = next(
        (
            item
            for item in workouts
            if item.workout_id == workout_id
        ),
        None,
    )

    if workout is None:
        raise ValueError(
            f"Séance Atlas introuvable : {workout_id}"
        )

    next_day = workout.workout_date + timedelta(days=1)
    sessions_on_next_day = sum(
        item.workout_date == next_day
        for item in workouts
    )

    if status == "skipped":
        impact = UserWorkoutDecisionEngine().skip(
            workout,
            reason=reason,
            sessions_on_next_day=sessions_on_next_day,
        ).to_dict()
    elif status == "completed":
        impact = {
            "workout_id": workout.workout_id,
            "status": "completed",
            "action": "maintain",
            "recalculate_future_program": False,
            "removed_duration_minutes": 0,
            "removed_physiological_load": 0,
            "removed_biomechanical_load": 0,
            "shift_days": 0,
            "reason": reason,
            "explanations": [
                "La séance est déclarée effectuée.",
                "Atlas attendra le fichier FIT pour analyser "
                "la réalisation réelle et confirmer la correspondance.",
            ],
        }

    else:
        impact = {
            "workout_id": workout.workout_id,
            "status": "planned",
            "action": "restore",
            "recalculate_future_program": False,
            "removed_duration_minutes": 0,
            "removed_physiological_load": 0,
            "removed_biomechanical_load": 0,
            "shift_days": 0,
            "reason": reason or "Decision modifiee par l'utilisateur",
            "explanations": [
                "La seance est reactivee dans le programme.",
            ],
        }
    record = {
        "decided_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        **impact,
    }

    history = []
    if WORKOUT_DECISIONS_PATH.exists():
        with WORKOUT_DECISIONS_PATH.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            loaded = json.load(input_file)
            if isinstance(loaded, list):
                history = loaded

    history.append(record)
    WORKOUT_DECISIONS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = WORKOUT_DECISIONS_PATH.with_suffix(".json.tmp")

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            history,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    temporary.replace(WORKOUT_DECISIONS_PATH)
    return record


def load_latest_workout_decisions():
    """Retourne la dernière décision enregistrée pour chaque séance."""

    if not WORKOUT_DECISIONS_PATH.exists():
        return {}

    with WORKOUT_DECISIONS_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        history = json.load(input_file)

    if not isinstance(history, list):
        return {}

    latest = {}
    for decision in history:
        if not isinstance(decision, dict):
            continue
        workout_id = str(decision.get("workout_id") or "").strip()
        if workout_id:
            latest[workout_id] = decision

    return latest


def create_twin(payload):
    context = payload.get("context") or {}
    anatomy = context.get("anatomy") or {}
    patient_context = context.get("patient") or {}
    identity = patient_context.get("identity") or {}

    selected_name = (
        anatomy.get("name")
        or anatomy.get("id")
        or "Structure anatomique"
    )

    selected_type = str(anatomy.get("type") or "").lower()

    patient = Patient(
        nom="",
        prenom=identity.get("displayName") or "Utilisateur",
        age=calculate_age(identity.get("birthDate")),
        sexe=(
            identity.get("biologicalSex")
            or identity.get("gender")
            or ""
        ),
        taille=number(identity.get("heightCm")) / 100,
        poids=number(identity.get("weightKg")),
    )

    if "muscle" in selected_type:
        patient.muscles.append(selected_name)

    if "articulation" in selected_type:
        patient.articulations.append(selected_name)

    twin = DigitalTwin(patient)
    twin.attach_anatomy(anatomy)

    readiness = patient_context.get("readiness") or {}
    readiness_score = readiness.get("readiness_score")

    if readiness_score is not None:
        twin.update_metric(
            metric_name="physiology_readiness_score",
            value=number(readiness_score),
            source="anatomy-analysis-0.9",
        )

    current_load = patient_context.get("currentLoad") or {}
    acute_load = current_load.get("acute_load_7d")
    chronic_load = current_load.get("chronic_load_28d")

    if acute_load is not None:
        twin.update_metric(
            metric_name="acute_load_7d",
            value=number(acute_load),
            source="anatomy-analysis-0.9",
        )

    if chronic_load is not None:
        twin.update_metric(
            metric_name="chronic_load_28d",
            value=number(chronic_load),
            source="anatomy-analysis-0.9",
        )

    return twin



WELLNESS_DIRECTORY = (
    ROOT / "atlas-data" / "garmin" / "wellness-archives"
)
WELLNESS_CACHE_PATH = (
    ROOT / "atlas-data" / "private"
    / "garmin-wellness-snapshot-cache.json"
)


def _wellness_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sleep_duration_minutes(snapshot):
    """Retourne la durée Garmin normalisée, avec compatibilité ancien cache."""
    stored = getattr(snapshot, "sleep_duration_minutes", None)
    if stored is not None:
        return int(stored)

    total = 0
    found = False
    for level in snapshot.sleep_levels or []:
        if not isinstance(level, dict):
            continue
        name = str(
            level.get("sleep_level")
            or level.get("level")
            or level.get("activity_type")
            or ""
        ).lower()
        if "awake" in name or "éveil" in name:
            continue
        raw = (
            level.get("duration")
            or level.get("duration_seconds")
            or level.get("message_index_duration")
        )
        duration = _wellness_number(raw)
        if duration is None or duration <= 0:
            continue
        if duration > 172800:
            duration /= 1000
        if duration > 1440:
            duration /= 60
        total += round(duration)
        found = True
    return total if found and total > 0 else None

def _atlas_recovery_index(snapshot):
    """Indice Atlas transparent, normalisé uniquement sur les données disponibles."""
    components = []

    if snapshot.sleep_recovery_score is not None:
        components.append(("Récupération du sommeil", snapshot.sleep_recovery_score, 30))
    if snapshot.sleep_score is not None:
        components.append(("Sommeil", snapshot.sleep_score, 25))

    hrv = _wellness_number(snapshot.hrv_last_night_ms)
    lower = _wellness_number(snapshot.hrv_baseline_lower_ms)
    upper = _wellness_number(snapshot.hrv_baseline_upper_ms)
    if hrv is not None:
        if lower is not None and upper is not None and upper > lower:
            hrv_score = 70 + 30 * (hrv - lower) / (upper - lower)
        elif snapshot.hrv_weekly_average_ms:
            weekly = max(_wellness_number(snapshot.hrv_weekly_average_ms) or 1, 1)
            hrv_score = 80 + 20 * (hrv / weekly - 1)
        else:
            hrv_score = 75
        components.append(("VFC nocturne", max(0, min(100, hrv_score)), 30))

    stress = _wellness_number(snapshot.sleep_average_stress)
    if stress is not None:
        components.append(("Stress nocturne", max(0, 100 - stress * 2), 10))

    if snapshot.data_quality_score is not None:
        components.append(("Qualité des données", snapshot.data_quality_score, 5))

    total_weight = sum(weight for _, _, weight in components)
    score = (
        round(sum(value * weight for _, value, weight in components) / total_weight)
        if total_weight
        else None
    )
    return {
        "score": score,
        "components": [
            {"label": label, "score": round(value), "weight": weight}
            for label, value, weight in components
        ],
    }


def _daily_training_loads():
    """Agrège la charge Garmin sans bloquer les autres indicateurs."""
    if not EXECUTIONS_PATH.exists():
        return {}
    try:
        with EXECUTIONS_PATH.open("r", encoding="utf-8") as source:
            payload = json.load(source)
        loads = {}
        for item in payload if isinstance(payload, list) else []:
            if not isinstance(item, dict):
                continue
            day = str(item.get("start_time") or "")[:10]
            fingerprint = item.get("fingerprint") or {}
            value = _wellness_number(fingerprint.get("training_load"))
            if day and value is not None:
                loads[day] = round(loads.get(day, 0.0) + value, 1)
        return loads
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def _program_progress():
    """Calcule l'avancement du plan et identifie la prochaine séance."""
    if not PROGRAM_PATH.exists():
        return None
    try:
        workouts = TrainingProgramLoader().load(PROGRAM_PATH)
        dated = sorted(
            (
                workout.workout_date,
                workout,
            )
            for workout in workouts
            if getattr(workout, "workout_date", None) is not None
        )
        if not dated:
            return None
        today = date.today()
        elapsed = sum(day < today for day, _workout in dated)
        percent = round(100 * elapsed / len(dated))
        upcoming = next(
            ((day, workout) for day, workout in dated if day >= today),
            None,
        )
        next_workout = None
        if upcoming:
            workout_day, workout = upcoming
            next_workout = {
                "workout_id": getattr(workout, "workout_id", None),
                "date": workout_day.isoformat(),
                "title": getattr(workout, "title", "Séance planifiée"),
                "duration_minutes": getattr(
                    workout,
                    "estimated_duration_minutes",
                    None,
                ),
                "sport": getattr(workout, "sport", None),
                "objective": getattr(workout, "objective", None),
            }
        return {
            "percent": max(0, min(100, percent)),
            "elapsed_sessions": elapsed,
            "total_sessions": len(dated),
            "start_date": dated[0][0].isoformat(),
            "end_date": dated[-1][0].isoformat(),
            "next_workout": next_workout,
        }
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        return None


def _performance_comparison(history):
    """Compare le contexte précédant les séances les plus et moins réussies."""
    empty = {
        "available": False,
        "evaluated_sessions": 0,
        "message": (
            "Les séances doivent disposer d’un score d’exécution fiable "
            "avant de pouvoir comparer leur contexte physiologique."
        ),
    }
    if not EXECUTIONS_PATH.is_file() or not history:
        return empty
    try:
        with EXECUTIONS_PATH.open("r", encoding="utf-8") as source:
            executions = json.load(source)
    except (OSError, json.JSONDecodeError):
        return empty
    if not isinstance(executions, list):
        return empty

    history_by_day = {item.get("day"): item for item in history}
    evaluated = []
    for item in executions:
        if not isinstance(item, dict):
            continue
        match = item.get("atlas_workout_match") or {}
        execution = match.get("execution") or {}
        score = _wellness_number(
            execution.get("execution_score")
            or execution.get("target_compliance_score")
            or match.get("target_compliance_score")
        )
        day_text = str(item.get("start_time") or "")[:10]
        try:
            activity_day = date.fromisoformat(day_text)
        except ValueError:
            continue
        if score is None:
            continue

        preceding = []
        for offset in (1, 2, 3):
            observed = history_by_day.get(
                (activity_day - timedelta(days=offset)).isoformat()
            )
            if observed:
                preceding.append(observed)

        def contextual_mean(field):
            values = [
                _wellness_number(day.get(field))
                for day in preceding
            ]
            values = [value for value in values if value is not None]
            return round(sum(values) / len(values), 1) if values else None

        analysis = item.get("detailed_analysis") or {}
        evaluated.append({
            "score": round(score, 1),
            "day": day_text,
            "work_type": analysis.get("dominant_work_type"),
            "sleep": contextual_mean("sleep_score"),
            "hrv": contextual_mean("hrv_last_night_ms"),
            "recovery": contextual_mean("sleep_recovery_score"),
            "atlas_index": contextual_mean("atlas_index"),
        })

    if len(evaluated) < 2:
        return {**empty, "evaluated_sessions": len(evaluated)}

    ordered = sorted(evaluated, key=lambda item: item["score"])
    group_size = max(1, min(5, len(ordered) // 3))
    lower = ordered[:group_size]
    upper = ordered[-group_size:]

    def aggregate(group):
        result = {
            "sessions": len(group),
            "execution_score": round(
                sum(item["score"] for item in group) / len(group), 1
            ),
        }
        for source, target in (
            ("sleep", "sleep_score_before"),
            ("hrv", "hrv_before_ms"),
            ("recovery", "recovery_before"),
            ("atlas_index", "atlas_index_before"),
        ):
            values = [
                item[source] for item in group
                if item[source] is not None
            ]
            result[target] = (
                round(sum(values) / len(values), 1)
                if values else None
            )
        work_types = [
            str(item["work_type"]) for item in group
            if item.get("work_type")
        ]
        result["dominant_work_type"] = (
            max(set(work_types), key=work_types.count)
            if work_types else None
        )
        return result

    best = aggregate(upper)
    difficult = aggregate(lower)
    available_context = any(
        best.get(field) is not None or difficult.get(field) is not None
        for field in (
            "sleep_score_before",
            "hrv_before_ms",
            "recovery_before",
            "atlas_index_before",
        )
    )
    return {
        "available": available_context,
        "evaluated_sessions": len(evaluated),
        "best": best,
        "difficult": difficult,
        "message": (
            "Comparaison des trois jours précédant les séances les mieux "
            "et les moins bien exécutées. Elle décrit des associations, "
            "sans prétendre démontrer une cause."
        ),
    }


def _athlete_analysis(history):
    """Construit un rapport longitudinal factuel, sans diagnostic médical."""
    if not history:
        return None

    latest = history[-1]
    recent = history[-28:]
    valid_hrv = [
        item["hrv_last_night_ms"]
        for item in recent
        if item.get("hrv_last_night_ms") is not None
    ]
    valid_sleep = [
        item["sleep_score"]
        for item in recent
        if item.get("sleep_score") is not None
    ]
    valid_resting = [
        item["resting_heart_rate_bpm"]
        for item in recent
        if item.get("resting_heart_rate_bpm") is not None
    ]
    quality = [
        item["data_quality_score"]
        for item in recent
        if item.get("data_quality_score") is not None
    ]

    mean = lambda values: round(sum(values) / len(values), 1) if values else None
    hrv_mean = mean(valid_hrv)
    sleep_mean = mean(valid_sleep)
    resting_mean = mean(valid_resting)
    coverage = round(
        100 * sum(
            item.get("hrv_last_night_ms") is not None
            and item.get("sleep_score") is not None
            for item in recent
        ) / max(1, len(recent))
    )
    confidence = round((mean(quality) or 0) * 0.7 + coverage * 0.3)

    strengths = []
    vigilance = []
    priorities = []

    latest_hrv = latest.get("hrv_last_night_ms")
    latest_weekly = latest.get("hrv_weekly_average_ms")
    if latest_hrv is not None and latest_weekly is not None:
        if latest_hrv >= latest_weekly:
            strengths.append(
                f"VFC nocturne favorable : {round(latest_hrv)} ms, "
                f"au-dessus de la moyenne 7 jours ({round(latest_weekly)} ms)."
            )
        else:
            vigilance.append(
                f"VFC nocturne à {round(latest_hrv)} ms, sous la moyenne "
                f"7 jours ({round(latest_weekly)} ms) : surveiller la tendance."
            )

    if sleep_mean is not None and sleep_mean >= 75:
        strengths.append(
            f"Sommeil globalement solide sur 28 jours : score moyen {round(sleep_mean)}/100."
        )
    elif sleep_mean is not None:
        vigilance.append(
            f"Sommeil perfectible sur 28 jours : score moyen {round(sleep_mean)}/100."
        )

    if resting_mean is not None:
        strengths.append(
            f"Fréquence cardiaque de repos stable autour de {round(resting_mean)} bpm "
            "sur les données récentes."
        )

    if latest.get("sleep_duration_minutes") is None:
        vigilance.append(
            "Durée de sommeil absente du dernier instantané : le score est disponible, "
            "mais la durée doit être relue dans l’archive Garmin."
        )
    if latest.get("training_load") is None:
        vigilance.append(
            "Charge du jour non mesurée : aucune conclusion de surcharge n’est formulée."
        )

    priorities.extend([
        "Préserver la majorité du volume en endurance fondamentale et suivre la dérive cardiaque.",
        "Conserver un renforcement utile au coureur, progressif et compatible avec la récupération.",
        "N’augmenter l’intensité que si sommeil, VFC et ressenti convergent favorablement.",
    ])

    if not strengths:
        strengths.append("Historique Wellness suffisamment dense pour établir une référence personnelle.")
    if not vigilance:
        vigilance.append("Aucun signal isolé majeur ; continuer à observer les tendances plutôt qu’une seule journée.")

    return {
        "generated_for": latest.get("day"),
        "profile": "Profil d’endurance en construction longitudinale",
        "summary": (
            "Atlas croise les tendances de sommeil, VFC, fréquence cardiaque de repos, "
            "récupération et charge disponible. Les conclusions ci-dessous sont reliées "
            "aux données observées et distinguent clairement les informations manquantes."
        ),
        "strengths": strengths[:3],
        "vigilance": vigilance[:3],
        "priorities": priorities,
        "confidence": {
            "score": max(0, min(100, confidence)),
            "coverage_28d": coverage,
            "wellness_days": len(history),
            "quality_28d": round(mean(quality) or 0),
            "explanation": (
                "Confiance fondée sur la couverture sommeil + VFC des 28 derniers jours "
                "et sur la qualité technique des fichiers Garmin."
            ),
        },
        "performance_comparison": _performance_comparison(history),
        "benchmarks": {
            "hrv_28d": hrv_mean,
            "sleep_score_28d": sleep_mean,
            "resting_hr_28d": resting_mean,
        },
        "medical_notice": (
            "Analyse d’aide à l’entraînement, non diagnostique. Une douleur persistante "
            "ou un symptôme inhabituel nécessite un avis professionnel."
        ),
    }

def load_wellness_history(refresh_latest=True):
    """Retourne uniquement les mesures utiles au navigateur."""
    connector = GarminWellnessConnector(str(WELLNESS_DIRECTORY))
    snapshots = []
    source_status = "cache"

    if WELLNESS_CACHE_PATH.is_file():
        cached = connector._load_cache(WELLNESS_CACHE_PATH)
        for item in (cached.get("archives") or {}).values():
            if not isinstance(item, dict):
                continue
            try:
                snapshots.append(
                    connector._snapshot_from_dict(item.get("snapshot"))
                )
            except (TypeError, ValueError):
                continue

    if not snapshots:
        source_status = "archives"
        snapshots = connector.import_all_cached(WELLNESS_CACHE_PATH)

    snapshots = sorted(snapshots, key=lambda item: item.day)

    # Les anciens caches ne contenaient pas la durée : relire seulement
    # l’archive la plus récente, sans retraiter tout l’historique.
    if (
        refresh_latest
        and snapshots
        and getattr(snapshots[-1], "sleep_duration_minutes", None) is None
    ):
        archive_day = snapshots[-1].day.isoformat()
        candidates = sorted(
            WELLNESS_DIRECTORY.glob(f"{archive_day}*.zip")
        )
        latest_archive = candidates[-1] if candidates else None
        if latest_archive is not None and latest_archive.is_file():
            try:
                refreshed = connector.import_archive(latest_archive)
                snapshots[-1] = refreshed
                source_status = "cache + dernière archive"
            except (OSError, ValueError):
                pass

    training_loads = _daily_training_loads()
    history = []
    for snapshot in snapshots:
        atlas_index = _atlas_recovery_index(snapshot)
        day = snapshot.day.isoformat()
        history.append({
            "day": day,
            "atlas_index": atlas_index["score"],
            "atlas_index_components": atlas_index["components"],
            "sleep_duration_minutes": _sleep_duration_minutes(snapshot),
            "sleep_score": snapshot.sleep_score,
            "sleep_quality_score": snapshot.sleep_quality_score,
            "sleep_recovery_score": snapshot.sleep_recovery_score,
            "hrv_last_night_ms": snapshot.hrv_last_night_ms,
            "hrv_weekly_average_ms": snapshot.hrv_weekly_average_ms,
            "hrv_baseline_lower_ms": snapshot.hrv_baseline_lower_ms,
            "hrv_baseline_upper_ms": snapshot.hrv_baseline_upper_ms,
            "hrv_status": snapshot.hrv_status,
            "resting_heart_rate_bpm": snapshot.resting_heart_rate_bpm,
            "sleep_average_stress": snapshot.sleep_average_stress,
            "training_load": training_loads.get(day),
            "data_quality_score": snapshot.data_quality_score,
        })
    return {
        "ok": True,
        "count": len(history),
        "source_status": source_status,
        "latest": history[-1] if history else None,
        "history": history,
        "program_progress": _program_progress(),
        "athlete_analysis": _athlete_analysis(history),
        "index_explanation": {
            "title": "Indice Atlas de disponibilité",
            "summary": (
                "Synthèse quotidienne sur 100 de la récupération du sommeil, "
                "du sommeil global, de la VFC par rapport à votre référence, "
                "du stress nocturne et de la qualité des données."
            ),
            "warning": (
                "Cet indice guide l'entraînement ; il ne constitue pas "
                "un diagnostic médical."
            ),
        },
    }


CONVERSATION_JOURNAL_PATH = (
    ROOT / "atlas-data" / "private" / "atlas-conversation-journal.json"
)


def atlas_conversation(payload):
    """Évalue localement une adaptation guidée de la prochaine séance."""
    feeling = payload.get("feeling") or {}
    preference = str(payload.get("preference") or "planned").strip().lower()
    note = str(payload.get("note") or "").strip()
    selected_option = str(payload.get("selected_option") or "").strip().lower()
    if len(note) > 400:
        raise ValueError("La précision est limitée à 400 caractères.")

    try:
        wellness = load_wellness_history(
            refresh_latest=False
        ).get("latest")
    except (OSError, ValueError, json.JSONDecodeError):
        wellness = None

    program = _program_progress()
    next_workout = (program or {}).get("next_workout") or {}

    def numeric(mapping, name, fallback=None):
        try:
            current = mapping.get(name)
            return fallback if current is None else float(current)
        except (AttributeError, TypeError, ValueError):
            return fallback

    energy = numeric(feeling, "energy", 6)
    fatigue = numeric(feeling, "fatigue", 3)
    pain = numeric(feeling, "pain", 0)
    atlas_index = numeric(wellness or {}, "atlas_index", 60)
    recovery = numeric(wellness or {}, "sleep_recovery_score")
    sleep_score = numeric(wellness or {}, "sleep_score")
    hrv = numeric(wellness or {}, "hrv_last_night_ms")
    hrv_week = numeric(wellness or {}, "hrv_weekly_average_ms")

    score = atlas_index
    reasons = [f"Indice Atlas {round(atlas_index)}/100"]
    if recovery is not None:
        reasons.append(f"Récupération {round(recovery)}/100")
    if sleep_score is not None:
        reasons.append(f"Sommeil {round(sleep_score)}/100")
    if hrv is not None:
        hrv_reason = f"VFC {round(hrv)} ms"
        if hrv_week is not None:
            hrv_reason += f" (référence 7 j : {round(hrv_week)} ms)"
            if hrv < hrv_week * 0.9:
                score -= 10
        reasons.append(hrv_reason)

    if energy <= 4:
        score -= 10
    elif energy >= 8:
        score += 4
    if fatigue >= 8:
        score -= 20
    elif fatigue >= 6:
        score -= 10
    if pain >= 8:
        score = min(score, 35)
    elif pain >= 5:
        score = min(score, 50)
    elif pain >= 2:
        score -= 5
    score = round(max(0, min(100, score)))

    planned_title = next_workout.get("title") or "la séance prévue"
    planned_date = next_workout.get("date")
    planned_text = planned_title + (
        f" ({planned_date})" if planned_date else ""
    )

    if pain >= 5 or score < 60:
        recommended = "replace"
        title = "Récupération prioritaire"
        explanation = (
            f"Les signaux du jour ne justifient pas une séance exigeante. "
            f"Atlas propose de remplacer {planned_text} par récupération, "
            "mobilité douce ou vélo très facile."
        )
    elif score < 75:
        recommended = "lighten"
        title = "Séance à alléger"
        explanation = (
            f"Votre disponibilité ajustée est intermédiaire. Atlas propose "
            f"de conserver l’objectif de {planned_text}, mais avec moins de "
            "volume et sans intensité supplémentaire."
        )
    else:
        recommended = "keep"
        title = "Séance compatible"
        explanation = (
            f"Les données et votre ressenti sont compatibles avec "
            f"{planned_text}. Conservez la séance prévue et contrôlez les "
            "sensations pendant l’échauffement."
        )

    if preference in {"threshold", "vo2max"} and score < 80:
        recommended = "lighten"
        title = "Intensité non prioritaire"
        explanation = (
            "Votre demande de séance qualitative est comprise, mais la marge "
            "du jour reste insuffisante pour ajouter une intensité improvisée. "
            "Atlas privilégie une endurance facile ou la séance prévue allégée."
        )
    elif preference == "rest":
        recommended = "replace"
        title = "Repos choisi"
        explanation = (
            "Votre préférence pour le repos est cohérente avec une adaptation "
            "prudente. Atlas propose mobilité douce ou repos complet."
        )

    option_definitions = [
        {
            "id": "keep",
            "title": "Conserver",
            "description": f"Maintenir {planned_text}.",
        },
        {
            "id": "lighten",
            "title": "Alléger",
            "description": (
                "Réduire le volume de 25 à 35 %, rester en endurance facile "
                "et supprimer l’intensité."
            ),
        },
        {
            "id": "replace",
            "title": "Remplacer",
            "description": (
                "Choisir repos, mobilité douce ou vélo très facile selon "
                "la douleur et la fatigue."
            ),
        },
    ]
    options = [
        {**option, "recommended": option["id"] == recommended}
        for option in option_definitions
    ]

    assessment = {
        "recorded_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "score": score,
        "title": title,
        "recommended_option": recommended,
        "evidence": reasons,
        "feeling": {
            "energy": energy,
            "fatigue": fatigue,
            "pain": pain,
        },
        "preference": preference,
        "note": note or None,
        "workout": next_workout or None,
        "selected_option": selected_option or None,
    }

    if selected_option:
        valid_options = {option["id"] for option in option_definitions}
        if selected_option not in valid_options:
            raise ValueError("Choix d’adaptation non pris en charge.")
        selected = next(
            option
            for option in option_definitions
            if option["id"] == selected_option
        )
        response = (
            f"« {selected['title']} » est enregistré dans le journal Atlas "
            "pour la prochaine séance. Le programme source reste inchangé "
            "tant que l’adaptation du calendrier n’a pas été confirmée."
        )
    else:
        response = explanation

    history = []
    if CONVERSATION_JOURNAL_PATH.exists():
        try:
            with CONVERSATION_JOURNAL_PATH.open(
                "r", encoding="utf-8"
            ) as source:
                loaded = json.load(source)
                if isinstance(loaded, list):
                    history = loaded
        except (OSError, json.JSONDecodeError):
            history = []
    history.append({
        "type": "guided_adaptation",
        **assessment,
        "response": response,
    })
    CONVERSATION_JOURNAL_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )
    temporary = CONVERSATION_JOURNAL_PATH.with_suffix(".json.tmp")
    with temporary.open(
        "w", encoding="utf-8", newline="\n"
    ) as output:
        json.dump(
            history[-500:],
            output,
            ensure_ascii=False,
            indent=2,
        )
    temporary.replace(CONVERSATION_JOURNAL_PATH)

    return {
        "response": response,
        "mode": "Moteur Atlas local et explicable",
        "assessment": assessment,
        "options": options,
    }

class AtlasRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(ROOT),
            **kwargs,
        )

    def log_message(self, format, *args):
        """Journalise les requêtes sans dépendre d'une console."""

        log_path = (
            ROOT
            / "atlas-data"
            / "private"
            / "atlas-web-server.log"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with log_path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as log_file:
            log_file.write(
                f"{datetime.now().astimezone().isoformat(timespec='seconds')}"
                f" | {self.address_string()} | "
                f"{format % args}\n"
            )

    def send_json(self, status, data):
        content = json.dumps(
            data,
            ensure_ascii=False,
            default=serialize,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(content)),
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)

        query = parse_qs(parsed.query)

        if parsed.path == "/api/atlas-coach/optional-workouts":
            try:
                workouts = []
                if OPTIONAL_WORKOUTS_PATH.exists():
                    with OPTIONAL_WORKOUTS_PATH.open(
                        "r", encoding="utf-8"
                    ) as source:
                        loaded = json.load(source)
                        if isinstance(loaded, list):
                            workouts = loaded
                self.send_json(200, {
                    "ok": True,
                    "workouts": workouts,
                })
            except (OSError, json.JSONDecodeError) as error:
                self.send_json(
                    500,
                    {"ok": False, "error": str(error)},
                )
            return

        if parsed.path == "/api/atlas/wellness-history":
            try:
                self.send_json(200, load_wellness_history())
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(
                    500,
                    {
                        "ok": False,
                        "error": (
                            "Les données Wellness ne peuvent pas "
                            f"être chargées : {error}"
                        ),
                    },
                )
            return

        if parsed.path == "/api/atlas-coach/workout-decisions":
            try:
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "decisions": load_latest_workout_decisions(),
                    },
                )
            except (OSError, json.JSONDecodeError) as error:
                self.send_json(
                    500,
                    {"ok": False, "error": str(error)},
                )
            return

        if parsed.path == "/api/atlas-coach/daily-preparation":
            try:
                workout_id = str(
                    (query.get("workout_id") or [""])[0]
                ).strip()
                if not workout_id:
                    raise ValueError("workout_id est obligatoire.")

                service = DailyPreparationService(ROOT)
                preparation = service.latest(workout_id)
                recorded = preparation is not None
                if preparation is None:
                    preparation = service.prepare(
                        workout_id,
                        {"checkpoint_type": "morning"},
                    )

                self.send_json(
                    200,
                    {
                        "ok": True,
                        "recorded": recorded,
                        "preparation": preparation,
                        "selection": service.latest_selection(workout_id),
                    },
                )
            except ValueError as error:
                self.send_json(
                    400,
                    {"ok": False, "error": str(error)},
                )
            except (OSError, json.JSONDecodeError) as error:
                self.send_json(
                    500,
                    {"ok": False, "error": str(error)},
                )
            return
        if parsed.path == "/api/atlas-coach/workout-context":
            try:
                workout_id = str(
                    (query.get("workout_id") or [""])[0]
                ).strip()
                if not workout_id:
                    raise ValueError("workout_id est obligatoire.")

                context = latest_workout_context(workout_id)
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "context": context,
                    },
                )
            except ValueError as error:
                self.send_json(
                    400,
                    {"ok": False, "error": str(error)},
                )
            except (OSError, json.JSONDecodeError) as error:
                self.send_json(
                    500,
                    {
                        "ok": False,
                        "error": (
                            "Le contexte utilisateur "
                            f"ne peut pas être chargé : {error}"
                        ),
                    },
                )
            return

        if parsed.path != "/api/atlas-coach/executions":
            super().do_GET()
            return

        try:
            workout_id = str(
                (query.get("workout_id") or [""])[0]
            ).strip()
            activity_id = str(
                (query.get("activity_id") or [""])[0]
            ).strip()

            try:
                limit = int((query.get("limit") or ["25"])[0])
            except (TypeError, ValueError):
                limit = 25

            limit = max(1, min(limit, 100))
            summaries = load_execution_summaries()

            if workout_id:
                summaries = [
                    item
                    for item in summaries
                    if str(
                        item.get("workout_match", {}).get("workout_id")
                        or ""
                    ) == workout_id
                ]

            if activity_id:
                summaries = [
                    item
                    for item in summaries
                    if str(item.get("activity_id") or "") == activity_id
                ]

            summaries = summaries[:limit]
            self.send_json(
                200,
                {
                    "ok": True,
                    "count": len(summaries),
                    "executions": summaries,
                },
            )
        except (OSError, json.JSONDecodeError) as error:
            self.send_json(
                500,
                {
                    "ok": False,
                    "error": (
                        "Les comptes-rendus Atlas "
                        f"ne peuvent pas être chargés : {error}"
                    ),
                },
            )
    def do_POST(self):
        allowed_routes = {
            "/api/atlas-brain/analyse",
            "/api/atlas-coach/workout-decision",
            "/api/atlas-coach/workout-context",
            "/api/atlas-coach/optional-workout",
            "/api/atlas-coach/daily-preparation",
            "/api/atlas/conversation",
        }

        if self.path not in allowed_routes:
            self.send_json(
                404,
                {"ok": False, "error": "Route introuvable."},
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))

            if self.path == "/api/atlas/conversation":
                result = atlas_conversation(payload)
                self.send_json(200, {"ok": True, **result})
                return

            if self.path == "/api/atlas-coach/optional-workout":
                workout = record_optional_workout(payload)
                self.send_json(200, {"ok": True, "workout": workout})
                return

            if self.path == "/api/atlas-coach/daily-preparation":
                service = DailyPreparationService(ROOT)
                if payload.get("user_selection"):
                    selection = service.record_selection(payload)
                    self.send_json(
                        200,
                        {
                            "ok": True,
                            "selection": selection,
                            "preparation": service.latest(
                                selection["workout_id"]
                            ),
                        },
                    )
                else:
                    preparation = service.record(payload)
                    self.send_json(
                        200,
                        {
                            "ok": True,
                            "preparation": preparation,
                            "selection": service.latest_selection(
                                preparation["workout_id"]
                            ),
                        },
                    )
                return
            if self.path == "/api/atlas-coach/workout-context":
                context = record_workout_context(payload)
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "context": context,
                    },
                )
                return

            if self.path == "/api/atlas-coach/workout-decision":
                decision = record_workout_decision(payload)
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "decision": decision,
                    },
                )
                return

            twin = create_twin(payload)
            report = AtlasBrain().analyse(twin)
            self.send_json(
                200,
                {
                    "ok": True,
                    "analysedAt": datetime.now().isoformat(),
                    "report": asdict(report),
                },
            )

        except ValueError as error:
            self.send_json(
                400,
                {"ok": False, "error": str(error)},
            )
        except Exception as error:
            self.send_json(
                500,
                {"ok": False, "error": str(error)},
            )

if __name__ == "__main__":
    address = ("0.0.0.0", 8000)
    server = ThreadingHTTPServer(
        address,
        AtlasRequestHandler,
    )

    print(
        "ATLAS OS disponible sur "
        "http://localhost:8000/app/atlas-cockpit.html"
    )
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        print(
            "Accès smartphone (même Wi-Fi) : "
            f"http://{local_ip}:8000/app/atlas-cockpit.html"
        )
    except OSError:
        print(
            "Accès smartphone : utilisez l’adresse IPv4 du PC "
            "sur le port 8000."
        )
    print(
        "Passerelle Atlas Brain active sur "
        "/api/atlas-brain/analyse"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur ATLAS OS.")
    finally:
        server.server_close()
