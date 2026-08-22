"""
ATLAS OS — serveur web local avec passerelle Atlas Brain.
"""

from dataclasses import asdict, is_dataclass
from collections import defaultdict
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
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
from src.training.post_workout_context_analyzer import (
    PostWorkoutContextAnalyzer,
)
from src.training.user_workout_decision import UserWorkoutDecisionEngine
from src.training.subscription_access import (
    filter_program_for_subscription,
    normalize_tier,
)


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
SUBSCRIPTION_PATH = (
    ROOT / "atlas-data" / "private" / "atlas-subscription.json"
)


def load_subscription_entitlement():
    """Charge le droit local ; le compte fondateur conserve l'accès complet."""

    configured = os.environ.get("ATLAS_SUBSCRIPTION_TIER")
    account = {}
    if SUBSCRIPTION_PATH.is_file():
        try:
            with SUBSCRIPTION_PATH.open("r", encoding="utf-8") as source:
                loaded = json.load(source)
                if isinstance(loaded, dict):
                    account = loaded
        except (OSError, json.JSONDecodeError):
            account = {}

    tier = normalize_tier(
        configured
        or account.get("tier")
        or account.get("role")
        or "founder_admin"
    )
    return {
        "tier": tier,
        "account_id": account.get("account_id") or "local-founder",
        "display_name": account.get("display_name") or "Christophe",
    }


def load_authorized_training_program():
    """Retourne le programme filtré avant toute transmission au navigateur."""

    if not PROGRAM_PATH.is_file():
        raise FileNotFoundError("Aucun programme Atlas actif.")
    with PROGRAM_PATH.open("r", encoding="utf-8") as source:
        program = json.load(source)
    entitlement = load_subscription_entitlement()
    filtered = filter_program_for_subscription(
        program,
        entitlement["tier"],
    )
    filtered["access_control"]["account_id"] = entitlement["account_id"]
    filtered["access_control"]["display_name"] = entitlement["display_name"]
    return filtered


def load_historical_workouts(private_dir=None):
    """Restitue les séances des versions successives du programme.

    Une activation remplace le programme courant, mais ne doit pas effacer
    l'intention des séances déjà courues. Seules les séances sont exposées :
    les autres données privées des sauvegardes restent côté serveur.
    """

    directory = Path(private_dir) if private_dir else PROGRAM_PATH.parent
    paths = sorted(
        directory.glob("training-program*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    workouts = {}

    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as source:
                document = json.load(source)
        except (OSError, json.JSONDecodeError):
            continue

        week_groups = document.get("weeks") or []
        if not week_groups and isinstance(document.get("pilot"), dict):
            week_groups = document["pilot"].get("weeks") or []

        for week in week_groups:
            for workout in week.get("workouts") or []:
                workout_date = str(workout.get("workout_date") or "")[:10]
                workout_id = str(workout.get("workout_id") or "")
                if not workout_date or not workout_id:
                    continue
                key = (workout_date, workout_id)
                workouts.setdefault(
                    key,
                    {
                        **workout,
                        "archived_program": path != PROGRAM_PATH,
                        "program_archive": path.name,
                    },
                )

    return sorted(
        workouts.values(),
        key=lambda workout: (
            str(workout.get("workout_date") or ""),
            str(workout.get("workout_id") or ""),
        ),
    )

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
                    "recovery_compliance_score",
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
                    "recovery_compliance_score",
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
                    "session_type",
                    "physiological_load_score",
                    "biomechanical_load_score",
                    "work_duration_seconds",
                    "work_distance_meters",
                    "recovery_duration_seconds",
                    "recovery_distance_meters",
                    "partial_work_duration_seconds",
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
    """Agrège les comptes-rendus FIT actifs et archivés, sans dépendre du plan."""

    candidate_paths = {EXECUTIONS_PATH}
    if EXECUTIONS_PATH.parent.exists():
        candidate_paths.update(
            EXECUTIONS_PATH.parent.glob("atlas-coach-executions*.json")
        )
        candidate_paths.update(
            EXECUTIONS_PATH.parent.glob("*executions*.backup*.json")
        )

    items = []
    for path in sorted(candidate_paths):
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as source:
                loaded = json.load(source)
        except (OSError, json.JSONDecodeError):
            continue
        items.extend(loaded if isinstance(loaded, list) else [loaded])

    deduplicated = {}
    for item in items:
        summary = execution_summary(item)
        if summary is None:
            continue
        activity = summary.get("activity") or {}
        key = str(
            summary.get("activity_id")
            or (
                str(summary.get("start_time") or "")
                + "|"
                + str(activity.get("distance_km") or "")
                + "|"
                + str(activity.get("duration_minutes") or "")
            )
        )
        deduplicated[key] = summary

    return sorted(
        deduplicated.values(),
        key=lambda item: str(item.get("start_time") or ""),
        reverse=True,
    )


def load_physiological_reference():
    """Relit les références physiologiques conservées dans le programme actif."""

    if not PROGRAM_PATH.is_file():
        return {}
    try:
        with PROGRAM_PATH.open("r", encoding="utf-8") as source:
            program = json.load(source)
    except (OSError, json.JSONDecodeError):
        return {}

    snapshot = program.get("athlete_snapshot") or {}
    sv1 = snapshot.get("sv1") or {}
    sv2 = snapshot.get("sv2") or {}
    return {
        "vo2_max": _wellness_number(snapshot.get("vo2_max")),
        "vma_kmh": _wellness_number(
            snapshot.get("vma_estimated_from_vo2_kmh")
            or snapshot.get("vma_kmh")
            or snapshot.get("vma_training_reference_kmh")
        ),
        "vma_training_reference_kmh": _wellness_number(
            snapshot.get("vma_training_reference_kmh")
            or snapshot.get("vma_kmh")
        ),
        "maximum_heart_rate_bpm": _wellness_number(
            snapshot.get("maximum_heart_rate_bpm")
        ),
        "resting_heart_rate_bpm": _wellness_number(
            snapshot.get("resting_heart_rate_bpm")
        ),
        "sv1_speed_kmh": _wellness_number(sv1.get("speed_kmh")),
        "sv1_heart_rate_bpm": _wellness_number(sv1.get("heart_rate_bpm")),
        "sv1_status": sv1.get("status"),
        "sv2_speed_kmh": _wellness_number(sv2.get("speed_kmh")),
        "sv2_heart_rate_bpm": _wellness_number(sv2.get("heart_rate_bpm")),
        "sv2_status": sv2.get("status"),
    }

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

    record = {
        "workout_id": workout_id,
        "activity_id": activity_id or None,
        "heat": bool(payload.get("heat")),
        "relief": bool(payload.get("relief")),
        "overall_sensation_0_to_10": context_score(
            payload.get("overall_sensation_0_to_10"),
            "La sensation générale",
        ),
        "perceived_effort_0_to_10": context_score(
            payload.get("perceived_effort_0_to_10"),
            "L'effort perçu",
        ),
        "heat_0_to_10": context_score(
            payload.get("heat_0_to_10"),
            "La chaleur ressentie",
        ),
        "relief_0_to_10": context_score(
            payload.get("relief_0_to_10"),
            "Le relief contraignant",
        ),
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
    record["atlas_interpretation"] = (
        PostWorkoutContextAnalyzer().analyze(record).to_dict()
    )

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

def _atlas_recovery_index(
    snapshot,
    *,
    training_load=None,
    training_load_baseline=None,
):
    """Indice Atlas transparent, normalisé uniquement sur les données disponibles."""
    components = []
    physiological_component_count = 0

    if snapshot.sleep_recovery_score is not None:
        components.append(("Récupération du sommeil", snapshot.sleep_recovery_score, 30))
        physiological_component_count += 1
    if snapshot.sleep_score is not None:
        components.append(("Sommeil", snapshot.sleep_score, 25))
        physiological_component_count += 1

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
        physiological_component_count += 1

    stress = _wellness_number(snapshot.sleep_average_stress)
    if stress is not None:
        components.append(("Stress nocturne", max(0, 100 - stress * 2), 10))
        physiological_component_count += 1

    # Une archive sans mesure physiologique ne doit jamais produire un faux
    # score de récupération à partir de la seule qualité technique ou charge.
    if not physiological_component_count:
        return {"score": None, "components": []}

    load = _wellness_number(training_load)
    load_baseline = _wellness_number(training_load_baseline)
    if load is not None:
        if load_baseline is not None and load_baseline > 0:
            load_ratio = load / load_baseline
            load_score = max(0, min(100, 100 - load_ratio * 35))
        else:
            load_score = 65
        components.append(("Charge sur 7 jours", load_score, 10))

    if (
        snapshot.data_quality_score is not None
        and snapshot.data_quality_score > 0
    ):
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


def _has_actionable_wellness(snapshot) -> bool:
    """Vrai si l'instantané peut réellement guider une décision d'entraînement."""
    quality = _wellness_number(getattr(snapshot, "data_quality_score", None))
    if quality is not None and quality <= 0:
        return False
    return any(
        _wellness_number(getattr(snapshot, field, None)) is not None
        for field in (
            "sleep_score",
            "sleep_recovery_score",
            "hrv_last_night_ms",
            "resting_heart_rate_bpm",
            "sleep_average_stress",
        )
    )


def _complete_wellness_calendar(history, end_day=None):
    """Conserve explicitement les jours absents entre deux mesures."""
    if not history:
        return []
    by_day = {str(item.get("day")): item for item in history if item.get("day")}
    start = date.fromisoformat(min(by_day))
    end = max(
        date.fromisoformat(max(by_day)),
        end_day or date.fromisoformat(max(by_day)),
    )
    complete = []
    current = start
    while current <= end:
        key = current.isoformat()
        if key in by_day:
            item = dict(by_day[key])
            item["data_present"] = True
            complete.append(item)
        else:
            complete.append({
                "day": key,
                "data_present": False,
                "source": None,
                "missing_reason": "Aucune archive Garmin Wellness pour cette date.",
            })
        current += timedelta(days=1)
    return complete


def _personal_baseline(history, index, field, days=28):
    """Calcule une référence antérieure sans utiliser la valeur du jour."""
    values = [
        _wellness_number(item.get(field))
        for item in history[max(0, index - days):index]
    ]
    valid = [value for value in values if value is not None]
    return round(sum(valid) / len(valid), 1) if len(valid) >= 3 else None


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

    contexts_by_workout = {}
    for context in load_workout_contexts():
        if not isinstance(context, dict):
            continue
        workout_id = str(context.get("workout_id") or "")
        if workout_id:
            contexts_by_workout[workout_id] = context

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
        workout_id = str(match.get("workout_id") or "")
        declared = contexts_by_workout.get(workout_id, {})
        evaluated.append({
            "score": round(score, 1),
            "day": day_text,
            "work_type": analysis.get("dominant_work_type"),
            "sleep": contextual_mean("sleep_score"),
            "hrv": contextual_mean("hrv_last_night_ms"),
            "recovery": contextual_mean("sleep_recovery_score"),
            "atlas_index": contextual_mean("atlas_index"),
            "perceived_effort": _wellness_number(
                declared.get("perceived_effort_0_to_10")
            ),
            "sensation": _wellness_number(
                declared.get("overall_sensation_0_to_10")
            ),
            "fatigue": _wellness_number(
                declared.get("fatigue_0_to_10")
            ),
            "pain": _wellness_number(
                declared.get("pain_0_to_10")
            ),
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
            ("perceived_effort", "perceived_effort_after"),
            ("sensation", "sensation_after"),
            ("fatigue", "fatigue_after"),
            ("pain", "pain_after"),
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
            "perceived_effort_after",
            "sensation_after",
            "fatigue_after",
            "pain_after",
        )
    )
    return {
        "available": available_context,
        "evaluated_sessions": len(evaluated),
        "best": best,
        "difficult": difficult,
        "message": (
            "Comparaison des trois jours précédant les séances et du ressenti "
            "déclaré après leur réalisation. Elle décrit des associations, "
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
    recent_week = recent[-7:]
    previous_period = recent[:-7]

    def field_mean(items, field):
        return mean([item[field] for item in items if item.get(field) is not None])

    def change(field):
        current = field_mean(recent_week, field)
        previous = field_mean(previous_period, field)
        if current is None or previous is None:
            return None
        return round(current - previous, 1)
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
    latest_day = None
    try:
        latest_day = date.fromisoformat(str(latest.get("day"))[:10])
    except (TypeError, ValueError):
        pass
    freshness_days = max(0, (date.today() - latest_day).days) if latest_day else None
    freshness_penalty = (
        min(45, max(0, freshness_days - 2) * 4)
        if freshness_days is not None else 25
    )
    confidence = round(
        (mean(quality) or 0) * 0.7 + coverage * 0.3 - freshness_penalty
    )

    strengths = []
    vigilance = []
    priorities = []
    physiology = load_physiological_reference()
    longitudinal_report = _longitudinal_training_report(history)

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
    if freshness_days is None:
        vigilance.append("Date du dernier instantané Wellness illisible : synchronisation à vérifier.")
    elif freshness_days > 2:
        vigilance.append(
            f"Dernières données Wellness âgées de {freshness_days} jours : "
            "la disponibilité du jour ne doit pas être déduite de cet instantané."
        )

    vo2_max = physiology.get("vo2_max")
    vma = physiology.get("vma_kmh")
    sv1_speed = physiology.get("sv1_speed_kmh")
    sv2_speed = physiology.get("sv2_speed_kmh")
    if vo2_max is not None:
        strengths.append(
            f"Capacité aérobie de référence : VO₂max {vo2_max:.0f} ml/kg/min."
        )
    if vma is not None:
        strengths.append(
            f"Vitesse aérobie de référence : VMA estimée {vma:.2f} km/h."
        )
    if sv1_speed is not None and sv2_speed is not None:
        strengths.append(
            f"Seuils physiologiques suivis : SV1 {sv1_speed:.1f} km/h et "
            f"SV2 {sv2_speed:.1f} km/h."
        )

    for conclusion in longitudinal_report.get("conclusions", []):
        topic = str(conclusion.get("topic") or "")
        statement = str(conclusion.get("conclusion") or "")
        evidence = str(conclusion.get("evidence") or "")
        combined = f"{topic} : {statement} {evidence}".strip()
        lowered = statement.lower()
        if any(word in lowered for word in (
            "progression", "régulier", "stable", "compatible", "sans hausse"
        )):
            strengths.append(combined)
        elif any(word in lowered for word in (
            "retrait", "surveiller", "variable", "défavorablement", "suspendre"
        )):
            vigilance.append(combined)

    priorities.extend([
        "Préserver la majorité du volume en endurance fondamentale et suivre la dérive cardiaque.",
        "Utiliser les tendances FIT allure/FC, charge et exécution pour ajuster la progression.",
        "N’augmenter l’intensité que si sommeil, VFC, exécution FIT et ressenti convergent favorablement.",
    ])

    if not strengths:
        strengths.append("Historique Wellness suffisamment dense pour établir une référence personnelle.")
    if not vigilance:
        vigilance.append("Aucun signal isolé majeur ; continuer à observer les tendances plutôt qu’une seule journée.")

    return {
        "generated_for": latest.get("day"),
        "profile": "Profil d’endurance en construction longitudinale",
        "summary": (
            "Atlas croise les tendances Wellness, les références physiologiques et "
            "les séances FIT actives ou archivées. Les forces, vigilances et priorités "
            "sont reliées aux données observées, indépendamment du programme en cours."
        ),
        "strengths": strengths[:5],
        "vigilance": vigilance[:5],
        "priorities": priorities,
        "confidence": {
            "score": max(0, min(100, confidence)),
            "coverage_28d": coverage,
            "wellness_days": len(history),
            "quality_28d": round(mean(quality) or 0),
            "freshness_days": freshness_days,
            "valid_hrv_days": len(valid_hrv),
            "valid_sleep_days": len(valid_sleep),
            "explanation": (
                "Confiance fondée sur la couverture sommeil + VFC des 28 derniers jours "
                "et sur la qualité technique des fichiers Garmin. Une synchronisation "
                "ancienne réduit automatiquement ce score."
            ),
        },
        "performance_comparison": _performance_comparison(history),
        "longitudinal_report": longitudinal_report,
        "physiology": physiology,
        "benchmarks": {
            "hrv_28d": hrv_mean,
            "sleep_score_28d": sleep_mean,
            "resting_hr_28d": resting_mean,
            "hrv_change_7d": change("hrv_last_night_ms"),
            "sleep_change_7d": change("sleep_score"),
            "resting_hr_change_7d": change("resting_heart_rate_bpm"),
        },
        "medical_notice": (
            "Analyse d’aide à l’entraînement, non diagnostique. Une douleur persistante "
            "ou un symptôme inhabituel nécessite un avis professionnel."
        ),
    }


def _longitudinal_training_report(wellness_history):
    """Argumente le profil avec les activités réellement analysées."""
    executions = load_execution_summaries()
    contexts = load_workout_contexts()
    conclusions = []
    missing = []

    recent_wellness = wellness_history[-7:]
    previous_wellness = wellness_history[-28:-7]

    def wellness_values(items, field):
        return [float(item[field]) for item in items if item.get(field) is not None]

    def add_wellness_trend(topic, field, unit, favorable_up=True):
        recent_values = wellness_values(recent_wellness, field)
        previous_values = wellness_values(previous_wellness, field)
        if len(recent_values) < 3 or len(previous_values) < 3:
            missing.append(
                f"Données {topic.lower()} insuffisantes pour comparer 7 jours à la référence antérieure."
            )
            return
        recent_mean = sum(recent_values) / len(recent_values)
        previous_mean = sum(previous_values) / len(previous_values)
        delta = recent_mean - previous_mean
        favorable = delta >= 0 if favorable_up else delta <= 0
        stable_margin = 1.0 if field != "hrv_last_night_ms" else 2.0
        if abs(delta) <= stable_margin:
            conclusion = f"{topic} globalement stable sur les 7 derniers jours disponibles."
        elif favorable:
            conclusion = f"{topic} évolue favorablement sur les 7 derniers jours disponibles."
        else:
            conclusion = f"{topic} évolue défavorablement et mérite une surveillance."
        quality = wellness_values(recent_wellness + previous_wellness, "data_quality_score")
        quality_mean = sum(quality) / len(quality) if quality else 0
        confidence = min(95, round(35 + (len(recent_values) + len(previous_values)) * 2 + quality_mean * 0.25))
        conclusions.append({
            "topic": topic,
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": (
                f"Moyenne 7 j {recent_mean:.1f}{unit}, référence précédente "
                f"{previous_mean:.1f}{unit}, écart {delta:+.1f}{unit}."
            ),
        })

    add_wellness_trend("VFC", "hrv_last_night_ms", " ms", favorable_up=True)
    add_wellness_trend("Sommeil", "sleep_score", "/100", favorable_up=True)
    add_wellness_trend(
        "Fréquence cardiaque au repos",
        "resting_heart_rate_bpm",
        " bpm",
        favorable_up=False,
    )
    add_wellness_trend(
        "Récupération",
        "sleep_recovery_score",
        "/100",
        favorable_up=True,
    )

    running = [
        item for item in executions
        if (item.get("activity") or {}).get("sport") in {
            "running", "run", "road_running", "trail"
        }
    ]
    weeks = defaultdict(lambda: {"distance": 0.0, "sessions": 0})
    for item in running:
        try:
            started = datetime.fromisoformat(str(item.get("start_time")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        activity = item.get("activity") or {}
        key = started.isocalendar()[:2]
        weeks[key]["distance"] += float(activity.get("distance_km") or 0)
        weeks[key]["sessions"] += 1

    if weeks:
        values = list(weeks.values())
        distances = [item["distance"] for item in values]
        sessions = [item["sessions"] for item in values]
        average_distance = sum(distances) / len(distances)
        average_sessions = sum(sessions) / len(sessions)
        confidence = min(95, 45 + len(running) * 3 + min(20, len(weeks) * 2))
        conclusions.append({
            "topic": "Volume et fréquence",
            "conclusion": (
                f"{average_distance:.1f} km et {average_sessions:.1f} séances de course "
                f"par semaine sur {len(weeks)} semaines observées."
            ),
            "confidence": confidence,
            "evidence": f"{len(running)} activités de course analysées.",
        })
        if len(distances) >= 4 and average_distance > 0:
            spread = (max(distances) - min(distances)) / average_distance * 100
            label = "régulier" if spread <= 35 else "variable"
            conclusions.append({
                "topic": "Régularité",
                "conclusion": f"Volume hebdomadaire {label} sur la période analysée.",
                "confidence": min(90, 50 + len(weeks) * 4),
                "evidence": f"Amplitude observée : {spread:.0f} % de la moyenne.",
            })
        if len(distances) >= 2 and distances[-2] > 0:
            change = (distances[-1] / distances[-2] - 1) * 100
            conclusion = (
                "Hausse de charge hebdomadaire à surveiller."
                if change > 20 else "Variation récente du volume sans hausse supérieure à 20 %."
            )
            conclusions.append({
                "topic": "Risque lié à la charge",
                "conclusion": conclusion,
                "confidence": min(90, 55 + len(weeks) * 3),
                "evidence": f"Variation entre les deux dernières semaines : {change:+.1f} %.",
            })
    else:
        missing.append("Historique d'activités analysées insuffisant pour calculer volume et fréquence.")

    valid_efficiency = []
    for item in running:
        activity = item.get("activity") or {}
        speed = activity.get("average_speed_kmh")
        heart_rate = activity.get("average_heart_rate_bpm")
        integrity = (item.get("analysis") or {}).get("data_integrity") or {}
        if speed and heart_rate and integrity.get("heart_rate_reliable", True):
            valid_efficiency.append(float(speed) / float(heart_rate) * 100)
    if len(valid_efficiency) >= 4:
        split = max(2, len(valid_efficiency) // 2)
        first = sum(valid_efficiency[:split]) / len(valid_efficiency[:split])
        second_values = valid_efficiency[split:]
        if second_values:
            second = sum(second_values) / len(second_values)
            change = (second / first - 1) * 100
            conclusions.append({
                "topic": "Relation allure / fréquence cardiaque",
                "conclusion": "Efficacité aérobie en progression." if change > 2 else (
                    "Efficacité aérobie en retrait." if change < -2 else "Efficacité aérobie globalement stable."
                ),
                "confidence": min(90, 45 + len(valid_efficiency) * 4),
                "evidence": f"Évolution de la vitesse par battement : {change:+.1f} %.",
            })
    else:
        missing.append("Au moins quatre séances avec allure et FC fiables sont nécessaires pour la tendance allure/FC.")

    threshold_observations = []
    for item in executions:
        threshold_observations.extend(
            (item.get("analysis") or {}).get("threshold_observations") or []
        )
    if threshold_observations:
        confidence = round(sum(
            float(item.get("confidence_score") or 0) for item in threshold_observations
        ) / len(threshold_observations))
        conclusions.append({
            "topic": "Seuils",
            "conclusion": "Des observations de terrain SV1/SV2 sont disponibles, mais restent à confirmer longitudinalement.",
            "confidence": confidence,
            "evidence": f"{len(threshold_observations)} observation(s) détectée(s).",
        })
    else:
        missing.append("Aucune observation FIT suffisamment structurée pour confirmer SV1 ou SV2.")

    intense_ids = {
        str(item.get("workout_match", {}).get("workout_id") or "")
        for item in executions
        if (item.get("analysis") or {}).get("session_type") in {"threshold", "vma", "tempo"}
    }
    intense_contexts = [
        item for item in contexts if str(item.get("workout_id") or "") in intense_ids
    ]
    if intense_contexts:
        fatigue = [float(item["fatigue_0_to_10"]) for item in intense_contexts if item.get("fatigue_0_to_10") is not None]
        pain = [float(item["pain_0_to_10"]) for item in intense_contexts if item.get("pain_0_to_10") is not None]
        if fatigue or pain:
            mean_fatigue = sum(fatigue) / len(fatigue) if fatigue else None
            mean_pain = sum(pain) / len(pain) if pain else None
            alert = (mean_fatigue is not None and mean_fatigue >= 6) or (mean_pain is not None and mean_pain >= 4)
            evidence = []
            if mean_fatigue is not None:
                evidence.append(f"fatigue {mean_fatigue:.1f}/10")
            if mean_pain is not None:
                evidence.append(f"douleur {mean_pain:.1f}/10")
            conclusions.append({
                "topic": "Tolérance aux séances intenses",
                "conclusion": "Tolérance à surveiller avant de progresser." if alert else "Tolérance déclarée compatible avec le maintien prudent de l'intensité.",
                "confidence": min(90, 45 + len(intense_contexts) * 8),
                "evidence": f"{len(intense_contexts)} retour(s) : " + ", ".join(evidence) + ".",
            })
    else:
        missing.append("Ressentis post-séance insuffisants pour conclure sur la tolérance à l'intensité.")

    pain_contexts = [
        item for item in contexts if float(item.get("pain_0_to_10") or 0) >= 4
    ]
    if len(pain_contexts) >= 2:
        conclusions.append({
            "topic": "Douleurs récurrentes",
            "conclusion": "Douleur significative déclarée à plusieurs reprises ; progression à suspendre jusqu'à clarification.",
            "confidence": min(95, 55 + len(pain_contexts) * 10),
            "evidence": f"{len(pain_contexts)} déclarations avec douleur ≥ 4/10.",
        })

    if not any(item.get("vo2_max") is not None for item in wellness_history):
        missing.append("VO₂max longitudinal non disponible dans les instantanés Wellness actuels.")

    return {
        "activity_count": len(executions),
        "running_activity_count": len(running),
        "wellness_day_count": len(wellness_history),
        "conclusions": conclusions,
        "missing_data": missing,
        "notice": "Chaque conclusion indique ses preuves et sa confiance ; les données absentes restent explicitement absentes.",
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
        and _has_actionable_wellness(snapshots[-1])
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
    for index, snapshot in enumerate(snapshots):
        day = snapshot.day.isoformat()
        recent_load_values = [
            value for previous_day, value in training_loads.items()
            if 0 <= (snapshot.day - date.fromisoformat(previous_day)).days <= 6
            and value is not None
        ]
        baseline_load_values = [
            value for previous_day, value in training_loads.items()
            if 7 <= (snapshot.day - date.fromisoformat(previous_day)).days <= 34
            and value is not None
        ]
        recent_load = round(sum(recent_load_values), 1) if recent_load_values else None
        load_baseline = (
            round(sum(baseline_load_values) / 4, 1)
            if len(baseline_load_values) >= 3 else None
        )
        atlas_index = _atlas_recovery_index(
            snapshot,
            training_load=recent_load,
            training_load_baseline=load_baseline,
        )
        item = {
            "day": day,
            "source": snapshot.source,
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
            "training_load_7d": recent_load,
            "training_load_baseline": load_baseline,
            "data_quality_score": snapshot.data_quality_score,
        }
        history.append(item)

    for index, item in enumerate(history):
        item["atlas_index_baseline"] = _personal_baseline(
            history, index, "atlas_index"
        )
        item["sleep_score_baseline"] = _personal_baseline(
            history, index, "sleep_score"
        )
        item["sleep_duration_baseline_minutes"] = _personal_baseline(
            history, index, "sleep_duration_minutes"
        )
        item["sleep_stress_baseline"] = _personal_baseline(
            history, index, "sleep_average_stress"
        )
        item["sleep_recovery_baseline"] = _personal_baseline(
            history, index, "sleep_recovery_score"
        )
        lower = _wellness_number(item.get("hrv_baseline_lower_ms"))
        upper = _wellness_number(item.get("hrv_baseline_upper_ms"))
        item["hrv_personal_baseline_ms"] = (
            round((lower + upper) / 2, 1)
            if lower is not None and upper is not None else
            _personal_baseline(history, index, "hrv_last_night_ms")
        )
    actionable_history = [
        item for item, snapshot in zip(history, snapshots)
        if _has_actionable_wellness(snapshot)
    ]
    latest_observation = history[-1] if history else None
    latest = actionable_history[-1] if actionable_history else None
    latest_unavailable = (
        {
            "day": latest_observation.get("day"),
            "reason": "Données physiologiques absentes ou incomplètes",
            "data_quality_score": latest_observation.get("data_quality_score"),
        }
        if latest_observation
        and (not latest or latest_observation.get("day") != latest.get("day"))
        else None
    )
    complete_history = _complete_wellness_calendar(
        history,
        end_day=date.today(),
    )
    return {
        "ok": True,
        "count": len(history),
        "calendar_day_count": len(complete_history),
        "source_status": source_status,
        "latest": latest,
        "latest_observation": latest_observation,
        "latest_unavailable": latest_unavailable,
        "history": complete_history,
        "program_progress": _program_progress(),
        "athlete_analysis": _athlete_analysis(actionable_history),
        "index_explanation": {
            "title": "Indice Atlas de disponibilité",
            "summary": (
                "Synthèse quotidienne sur 100 de la récupération du sommeil, "
                "du sommeil global, de la VFC par rapport à votre référence, "
                "du stress nocturne, de la charge récente et de la qualité des données."
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

    knowledge = {
        "knows": ["Votre ressenti déclaré dans cette fenêtre."],
        "does_not_know": [],
        "local": True,
    }
    try:
        wellness_payload = load_wellness_history(
            refresh_latest=False
        )
        wellness = wellness_payload.get("latest")
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
    for label, value in (("énergie", energy), ("fatigue", fatigue), ("douleur", pain)):
        if value is None or not 0 <= value <= 10:
            raise ValueError(f"Le score {label} doit être compris entre 0 et 10.")
    wellness_fresh = False
    if wellness and wellness.get("day"):
        try:
            wellness_age = (date.today() - date.fromisoformat(str(wellness["day"])[:10])).days
            wellness_fresh = wellness_age <= 2
        except ValueError:
            wellness_age = None
    else:
        wellness_age = None

    atlas_index = numeric(wellness or {}, "atlas_index") if wellness_fresh else None
    recovery = numeric(wellness or {}, "sleep_recovery_score")
    sleep_score = numeric(wellness or {}, "sleep_score")
    hrv = numeric(wellness or {}, "hrv_last_night_ms")
    hrv_week = numeric(wellness or {}, "hrv_weekly_average_ms")

    score = atlas_index if atlas_index is not None else 70
    reasons = []
    if atlas_index is not None:
        reasons.append(f"Indice Atlas {round(atlas_index)}/100")
        knowledge["knows"].append(
            f"Les données Garmin Wellness du {wellness.get('day')}."
        )
    else:
        knowledge["does_not_know"].append(
            "Votre disponibilité physiologique actuelle : les données Wellness sont absentes ou datent de plus de deux jours."
        )
        reasons.append("Décision principalement fondée sur le ressenti déclaré")
    if recovery is not None and wellness_fresh:
        reasons.append(f"Récupération {round(recovery)}/100")
    if sleep_score is not None and wellness_fresh:
        reasons.append(f"Sommeil {round(sleep_score)}/100")
    if hrv is not None and wellness_fresh:
        hrv_reason = f"VFC {round(hrv)} ms"
        if hrv_week is not None:
            hrv_reason += f" (référence 7 j : {round(hrv_week)} ms)"
            if hrv < hrv_week * 0.9:
                score -= 10
        reasons.append(hrv_reason)

    try:
        previous_contexts = load_workout_contexts()
    except (OSError, json.JSONDecodeError):
        previous_contexts = []
    if previous_contexts:
        latest_context = previous_contexts[-1]
        latest_fatigue = numeric(latest_context, "fatigue_0_to_10")
        latest_pain = numeric(latest_context, "pain_0_to_10")
        knowledge["knows"].append(
            "Le dernier ressenti post-séance enregistré dans Atlas."
        )
        if latest_fatigue is not None and latest_fatigue >= 6:
            score -= 5
            reasons.append(f"Dernière fatigue post-séance {latest_fatigue:.0f}/10")
        if latest_pain is not None and latest_pain >= 4:
            score -= 10
            reasons.append(f"Dernière douleur post-séance {latest_pain:.0f}/10")
    else:
        knowledge["does_not_know"].append(
            "Votre réponse à la dernière séance : aucun ressenti post-séance n’est enregistré."
        )

    if next_workout:
        knowledge["knows"].append("La prochaine séance inscrite au programme Atlas.")
    else:
        knowledge["does_not_know"].append("La prochaine séance : aucun programme exploitable n’est chargé.")

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
        "knowledge": knowledge,
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
        "knowledge": knowledge,
    }

class AtlasRequestHandler(SimpleHTTPRequestHandler):
    server_version = "AtlasOS/1.0"

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

        if parsed.path == "/api/atlas-coach/program":
            try:
                self.send_json(200, load_authorized_training_program())
            except (OSError, json.JSONDecodeError) as error:
                self.send_json(
                    404,
                    {"ok": False, "error": str(error)},
                )
            return

        if parsed.path == "/api/atlas-coach/historical-workouts":
            try:
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "workouts": load_historical_workouts(),
                    },
                )
            except OSError as error:
                self.send_json(500, {"ok": False, "error": str(error)})
            return

        if parsed.path in {
            "/atlas-data/private/training-program.json",
            "/atlas-data/private/three-plus-one-pilot-preview.json",
        }:
            self.send_json(
                403,
                {
                    "ok": False,
                    "error": "Programme protégé : utilisez l’API Atlas.",
                },
            )
            return

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
    try:
        port = int(os.environ.get("ATLAS_PORT", "8000"))
    except ValueError:
        port = 8000

    address = ("0.0.0.0", port)
    server = ThreadingHTTPServer(
        address,
        AtlasRequestHandler,
    )

    print(
        "ATLAS OS disponible sur "
        f"http://localhost:{port}/app/atlas-cockpit.html"
    )
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        print(
            "Accès smartphone (même Wi-Fi) : "
            f"http://{local_ip}:{port}/app/atlas-cockpit.html"
        )
    except OSError:
        print(
            "Accès smartphone : utilisez l’adresse IPv4 du PC "
            f"sur le port {port}."
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
