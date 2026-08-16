"""
ATLAS OS — préparation adaptative intrajournalière d'une séance.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from src.connectors.garmin_wellness import GarminWellnessConnector
from src.physiology.garmin_recovery_adapter import GarminRecoveryAdapter

from .adaptive_loop import AdaptiveTrainingLoop
from .training_program_loader import TrainingProgramLoader


CHECKPOINT_TYPES = {"morning", "post_nap", "pre_workout"}


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default

    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def _optional_score(value: Any, field_name: str) -> float | None:
    if value in (None, ""):
        return None

    score = float(value)
    if not 0 <= score <= 10:
        raise ValueError(f"{field_name} doit être compris entre 0 et 10.")
    return score


def _optional_minutes(value: Any) -> int | None:
    if value in (None, ""):
        return None

    minutes = int(value)
    if not 0 <= minutes <= 240:
        raise ValueError(
            "nap_duration_minutes doit être compris entre 0 et 240."
        )
    return minutes


class DailyPreparationService:
    """Relie le programme, le Wellness et le ressenti intrajournalier."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.program_path = (
            self.root / "atlas-data" / "private" / "training-program.json"
        )
        self.wellness_directory = (
            self.root / "atlas-data" / "garmin" / "wellness-archives"
        )
        self.wellness_cache_path = (
            self.root
            / "atlas-data"
            / "private"
            / "garmin-wellness-snapshot-cache.json"
        )
        self.fusion_path = (
            self.root
            / "atlas-data"
            / "private"
            / "training-history-fusion.json"
        )
        self.checkpoints_path = (
            self.root
            / "atlas-data"
            / "private"
            / "atlas-coach-readiness-checkpoints.json"
        )
        self.selections_path = (
            self.root
            / "atlas-data"
            / "private"
            / "atlas-coach-readiness-selections.json"
        )

    def prepare(
        self,
        workout_id: str,
        checkpoint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        checkpoint = checkpoint or {}
        workouts = TrainingProgramLoader().load(self.program_path)
        workout = next(
            (item for item in workouts if item.workout_id == workout_id),
            None,
        )
        if workout is None:
            raise ValueError(f"Séance Atlas introuvable : {workout_id}")

        connector = GarminWellnessConnector(self.wellness_directory)
        cache = connector._load_cache(self.wellness_cache_path)
        archives = cache.get("archives") or {}
        snapshots = [
            connector._snapshot_from_dict(item["snapshot"])
            for item in archives.values()
            if isinstance(item, dict) and item.get("snapshot")
        ]
        snapshots.sort(key=lambda item: item.day)

        available = [
            item for item in snapshots if item.day <= workout.workout_date
        ]
        if not available:
            raise ValueError(
                "Aucun Wellness disponible avant cette séance."
            )
        wellness = available[-1]

        fusion = _read_json(self.fusion_path, {})
        program = _read_json(self.program_path, {})
        athlete = program.get("athlete_snapshot") or {}

        fatigue = _optional_score(
            checkpoint.get("subjective_fatigue_0_to_10", checkpoint.get("subjective_fatigue_0_10")),
            "subjective_fatigue_0_10",
        )
        energy = _optional_score(
            checkpoint.get("energy_0_to_10", checkpoint.get("energy_0_10")),
            "energy_0_10",
        )
        if fatigue is None and energy is not None:
            fatigue = 10 - energy

        pain = _optional_score(
            checkpoint.get("pain_0_to_10", checkpoint.get("pain_0_10")),
            "pain_0_10",
        )
        soreness = _optional_score(
            checkpoint.get("muscle_soreness_0_to_10", checkpoint.get("muscle_soreness_0_10")),
            "muscle_soreness_0_10",
        )
        nap_minutes = _optional_minutes(
            checkpoint.get("nap_duration_minutes")
        )
        actual_sleep_hours = checkpoint.get("actual_sleep_hours")
        actual_sleep_hours = (
            None
            if actual_sleep_hours in (None, "")
            else float(actual_sleep_hours)
        )
        body_battery = checkpoint.get("body_battery_0_to_100", checkpoint.get("body_battery_0_100"))
        body_battery = (
            None
            if body_battery in (None, "")
            else int(body_battery)
        )
        recovery_hours = checkpoint.get("recovery_hours_remaining")
        recovery_hours = (
            None
            if recovery_hours in (None, "")
            else float(recovery_hours)
        )

        if actual_sleep_hours is not None and not 0 <= actual_sleep_hours <= 16:
            raise ValueError("actual_sleep_hours doit être compris entre 0 et 16.")
        if body_battery is not None and not 0 <= body_battery <= 100:
            raise ValueError("body_battery_0_100 doit être compris entre 0 et 100.")
        if recovery_hours is not None and not 0 <= recovery_hours <= 168:
            raise ValueError("recovery_hours_remaining doit être compris entre 0 et 168.")

        notes = [
            f"Évaluation {checkpoint.get('checkpoint_type', 'morning')}.",
        ]
        if nap_minutes is not None:
            notes.append(
                f"Sieste déclarée : {nap_minutes} minute(s)."
            )
        if body_battery is not None:
            notes.append(f"Body Battery : {body_battery}/100.")
        if recovery_hours is not None:
            notes.append(
                f"Récupération Garmin restante : {recovery_hours:g} h."
            )
        comment = str(checkpoint.get("comment") or "").strip()
        if comment:
            notes.append(comment[:1200])

        physiology_input = GarminRecoveryAdapter().build_input(
            wellness,
            snapshots,
            subjective_fatigue_0_10=fatigue,
            muscle_soreness_0_10=soreness,
            pain_0_10=pain,
            acute_load_7d=fusion.get("acute_load_7d"),
            chronic_load_28d=fusion.get(
                "chronic_load_28d_weekly"
            ),
            vo2max=athlete.get("vo2_max"),
            vo2max_baseline=athlete.get("vo2_max"),
            notes=" ".join(notes),
        )

        if actual_sleep_hours is not None:
            physiology_input.sleep_hours = actual_sleep_hours

        result = AdaptiveTrainingLoop().prepare_session(
            physiology_input,
            workout,
        )

        return {
            "generated_at": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "checkpoint_type": checkpoint.get(
                "checkpoint_type",
                "morning",
            ),
            "wellness_day": wellness.day.isoformat(),
            "workout_id": workout.workout_id,
            "physiology_input": asdict(physiology_input),
            "physiology": asdict(result.physiology),
            "atlas_index": asdict(result.atlas_index),
            "decision": asdict(result.decision),
            "adaptation": asdict(result.adaptation),
            "declared_state": {
                "actual_sleep_hours": actual_sleep_hours,
                "nap_duration_minutes": nap_minutes,
                "body_battery_0_to_100": body_battery,
                "body_battery_charged": checkpoint.get("body_battery_charged"),
                "body_battery_drained": checkpoint.get("body_battery_drained"),
                "recovery_hours_remaining": recovery_hours,
                "training_status": str(
                    checkpoint.get("training_status") or ""
                ).strip(),
                "energy_0_to_10": energy,
                "subjective_fatigue_0_to_10": fatigue,
                "pain_0_to_10": pain,
                "muscle_soreness_0_to_10": soreness,
                "comment": comment,
            },
        }

    def record(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        workout_id = str(payload.get("workout_id") or "").strip()
        if not workout_id:
            raise ValueError("workout_id est obligatoire.")

        checkpoint_type = str(
            payload.get("checkpoint_type") or "morning"
        ).strip()
        if checkpoint_type not in CHECKPOINT_TYPES:
            raise ValueError(
                "checkpoint_type doit être morning, post_nap "
                "ou pre_workout."
            )

        checkpoint = dict(payload)
        checkpoint["checkpoint_type"] = checkpoint_type
        preparation = self.prepare(workout_id, checkpoint)
        preparation["submitted_state"] = {
            key: value
            for key, value in checkpoint.items()
            if key != "workout_id"
        }

        history = _read_json(self.checkpoints_path, [])
        if not isinstance(history, list):
            history = []
        history.append(preparation)

        self.checkpoints_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary = self.checkpoints_path.with_suffix(
            self.checkpoints_path.suffix + ".tmp"
        )
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
                default=str,
            )
            output_file.write("\n")
        temporary.replace(self.checkpoints_path)
        return preparation

    def latest(
        self,
        workout_id: str,
    ) -> dict[str, Any] | None:
        history = _read_json(self.checkpoints_path, [])
        if not isinstance(history, list):
            return None

        matches = [
            item
            for item in history
            if isinstance(item, dict)
            and item.get("workout_id") == workout_id
        ]
        return matches[-1] if matches else None

    def record_selection(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Historise le choix explicite de l’utilisateur après proposition Atlas."""

        workout_id = str(payload.get("workout_id") or "").strip()
        if not workout_id:
            raise ValueError("workout_id est obligatoire.")

        selection = str(payload.get("user_selection") or "").strip()
        allowed = {
            "accept_adaptation",
            "keep_original",
            "decide_later",
        }
        if selection not in allowed:
            raise ValueError(
                "user_selection doit être accept_adaptation, "
                "keep_original ou decide_later."
            )

        preparation = self.latest(workout_id)
        if preparation is None:
            raise ValueError(
                "Aucune réévaluation Atlas enregistrée pour cette séance."
            )

        record = {
            "recorded_at": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "workout_id": workout_id,
            "user_selection": selection,
            "reason": str(payload.get("reason") or "").strip(),
            "preparation_generated_at": preparation.get("generated_at"),
            "checkpoint_type": preparation.get("checkpoint_type"),
            "atlas_index_score": (
                preparation.get("atlas_index") or {}
            ).get("score"),
            "atlas_action": (
                preparation.get("decision") or {}
            ).get("action"),
            "original_workout_id": preparation.get("workout_id"),
            "adapted_workout": (
                preparation.get("adaptation") or {}
            ).get("adapted_workout"),
        }

        history = _read_json(self.selections_path, [])
        if not isinstance(history, list):
            history = []
        history.append(record)

        self.selections_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary = self.selections_path.with_suffix(
            self.selections_path.suffix + ".tmp"
        )
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
                default=str,
            )
            output_file.write("\n")
        temporary.replace(self.selections_path)
        return record

    def latest_selection(
        self,
        workout_id: str,
    ) -> dict[str, Any] | None:
        history = _read_json(self.selections_path, [])
        if not isinstance(history, list):
            return None

        matches = [
            item
            for item in history
            if isinstance(item, dict)
            and item.get("workout_id") == workout_id
        ]
        return matches[-1] if matches else None