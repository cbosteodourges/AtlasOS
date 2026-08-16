"""
ATLAS OS — serveur web local avec passerelle Atlas Brain.
"""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.atlas_brain import AtlasBrain
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
    if status not in {"completed", "skipped"}:
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
    else:
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
            "/api/atlas-coach/daily-preparation",
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
    address = ("localhost", 8000)
    server = ThreadingHTTPServer(
        address,
        AtlasRequestHandler,
    )

    print(
        "ATLAS OS disponible sur "
        "http://localhost:8000/app/biomecanique.html"
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
