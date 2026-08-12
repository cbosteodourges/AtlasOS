"""
ATLAS OS — serveur web local avec passerelle Atlas Brain.
"""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.atlas_brain import AtlasBrain
from src.patient.patient import Patient
from src.twin.digital_twin import DigitalTwin
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

    def do_POST(self):
        allowed_routes = {
            "/api/atlas-brain/analyse",
            "/api/atlas-coach/workout-decision",
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
