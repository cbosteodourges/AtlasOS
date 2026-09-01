"""Boucle Atlas déclenchée après chaque synchronisation externe."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any

from src.connectors.activity_ingestion import ActivityStore
from src.physiology.atlas_recovery_index import AtlasRecoveryIndex
from src.physiology.continuous_profile import ContinuousPhysiologyEstimator
from src.physiology.nutrition_hydration import NutritionHydrationAnalyzer


PHYSIOLOGY_KEYS = {"vo2_max", "vma_kmh", "vma_training_reference_kmh",
                   "maximum_heart_rate_bpm", "sv1", "sv2"}
HEALTH_CONNECT_ANALYSIS_VERSION = 8


class PostSyncOrchestrator:
    """Recalcule les indicateurs et prépare un programme candidat explicable.

    Le programme actif n'est jamais réécrit : Atlas produit une proposition
    séparée qui doit être acceptée par l'utilisateur.
    """

    def __init__(self, private_dir: str | Path) -> None:
        self.private_dir = Path(private_dir)

    def run(self, source: str) -> dict[str, Any]:
        activities = ActivityStore(self.private_dir / "activities-unified.json").load()
        wellness = self._merged_wellness()
        manual_nutrition = self._read("nutrition-hydration-manual.json", [])
        analyzed_activities = self._refresh_activity_executions(activities)
        executions = self._read("atlas-coach-executions.json", [])
        recovery = AtlasRecoveryIndex().build(
            wellness,
            activities,
            outcomes=executions,
        )
        self._write("atlas-recovery-index.json", recovery)

        previous = self._current_physiology()
        estimate = ContinuousPhysiologyEstimator().estimate(activities, previous)
        proposed_profile = {
            **previous,
            **(
                {key: value for key, value in estimate.items() if key in PHYSIOLOGY_KEYS}
                if estimate.get("updated")
                else {}
            ),
        }
        # Le profil affiché et historisé reste la référence active. Une estimation
        # n'entre dans le profil qu'après validation explicite de la proposition.
        profile = previous
        longitudinal = self._read("physiology-longitudinal.json", {"current": previous, "history": []})
        history = [
            item for item in longitudinal.get("history", [])
            if item.get("schema") == "validated_profile_v1"
        ]
        history.extend(self._retrospective_physiology(activities, profile))
        today = date.today().isoformat()
        sv1 = profile.get("sv1") or {}
        sv2 = profile.get("sv2") or {}
        snapshot = {
            "day": today,
            "source": source,
            "schema": "validated_profile_v1",
            "vo2_max": profile.get("vo2_max"),
            "vma_kmh": (
                profile.get("vma_estimated_from_vo2_kmh")
                or profile.get("vma_kmh")
                or profile.get("vma_training_reference_kmh")
            ),
            "sv1_speed_kmh": sv1.get("speed_kmh"),
            "sv2_speed_kmh": sv2.get("speed_kmh"),
            "maximum_heart_rate_bpm": profile.get("maximum_heart_rate_bpm"),
            "estimator_updated": bool(estimate.get("updated")),
            "estimator_confidence": estimate.get("confidence"),
        }
        history = [item for item in history if str(item.get("day") or "")[:10] != today]
        history.append(snapshot)
        history.sort(key=lambda item: str(item.get("day") or ""))
        longitudinal = {"current": profile, "latest_estimate": estimate, "history": history[-5000:],
                        "updated_at": datetime.now(timezone.utc).isoformat()}
        self._write("physiology-longitudinal.json", longitudinal)

        latest = recovery.get("latest") or {}
        weights = sorted((item for item in wellness if item.get("type") == "weight"),
                         key=lambda item: str(item.get("start_time") or ""))
        weight = weights[-1].get("value") if weights else None
        exercise_minutes = sum(item.duration_seconds for item in activities
                               if item.start_time[:10] == date.today().isoformat()) / 60
        nutrition = NutritionHydrationAnalyzer().analyze(
            [*wellness, *manual_nutrition], weight_kg=weight,
            exercise_minutes_today=exercise_minutes,
        )
        self._write("nutrition-hydration-summary.json", nutrition)
        score = latest.get("atlas_recovery_index")
        action = self._action(score)
        proposal = self._program_proposal(proposed_profile, action, score, estimate, nutrition)
        assessment = {
            "source": source,
            "synchronized_at": datetime.now(timezone.utc).isoformat(),
            "recovery": latest,
            "physiology": estimate,
            "nutrition_hydration": nutrition,
            "program_action": action,
            "program_proposal_available": proposal is not None,
            "health_connect_activities_analyzed": analyzed_activities,
            "requires_user_validation": True,
        }
        self._write("daily-sync-assessment.json", assessment)
        if proposal is not None:
            self._write("training-program-sync-proposal.json", proposal)
        return assessment

    def _refresh_activity_executions(self, activities: list[Any]) -> int:
        """Analyse les activités Health Connect sans exiger de fichier FIT."""

        program_path = self.private_dir / "training-program.json"
        if not program_path.is_file():
            return 0

        # Le moteur utilisé par l'import FIT accepte déjà toute activité
        # normalisée. Health Connect passe donc exactement par les mêmes
        # analyses et le même rapprochement avec le programme.
        from scripts.sync_atlas_coach_pilot import (
            build_record,
            confirm_matched_workouts,
            load_analysis_profile,
            load_optional_workouts,
        )
        from src.training import TrainingProgramLoader

        loader = TrainingProgramLoader()
        workouts = loader.load(program_path)
        optional_path = (
            self.private_dir / "atlas-coach-optional-workouts.json"
        )
        if optional_path.is_file():
            workouts.extend(
                load_optional_workouts(optional_path, loader)
            )
        profile = load_analysis_profile(program_path)
        history = self._read("atlas-coach-executions.json", [])
        history = history if isinstance(history, list) else []
        by_activity = {
            str(item.get("activity_id") or ""): item
            for item in history
            if isinstance(item, dict)
        }
        refreshed = []

        for activity in activities:
            source_ids = getattr(activity, "source_ids", {}) or {}
            provider = str(getattr(activity, "provider", "") or "")
            if (
                "health_connect" not in source_ids
                and provider != "health_connect"
            ):
                continue
            activity_id = str(getattr(activity, "atlas_id", "") or "")
            previous = by_activity.get(activity_id)
            if (
                isinstance(previous, dict)
                and previous.get("atlas_workout_match") is not None
                and previous.get("health_connect_analysis_version")
                == HEALTH_CONNECT_ANALYSIS_VERSION
            ):
                continue
            try:
                record = build_record(
                    activity,
                    workouts,
                    loader,
                    profile,
                )
                record["health_connect_analysis_version"] = (
                    HEALTH_CONNECT_ANALYSIS_VERSION
                )
            except (TypeError, ValueError, KeyError):
                # Une activité ancienne incomplète ne doit jamais bloquer la
                # synchronisation des données récentes et du wellness.
                continue
            by_activity[activity_id] = record
            refreshed.append(record)

        if not refreshed:
            return 0

        updated = [
            item
            for item in history
            if str(item.get("activity_id") or "") not in {
                str(record.get("activity_id") or "")
                for record in refreshed
            }
        ]
        updated.extend(refreshed)
        updated.sort(key=lambda item: str(item.get("start_time") or ""))
        self._write("atlas-coach-executions.json", updated)
        confirm_matched_workouts(
            refreshed,
            self.private_dir / "atlas-coach-workout-decisions.json",
        )
        return len(refreshed)

    @staticmethod
    def _retrospective_physiology(activities: list[Any], profile: dict[str, Any]) -> list[dict[str, Any]]:
        """Reconstruit une tendance terrain hebdomadaire, puis l'ancre sur le profil validé."""

        runs = sorted(
            (
                item for item in activities
                if str(getattr(item, "activity_type", "")).lower()
                in {"run", "running", "trail_running", "56"}
            ),
            key=lambda item: str(getattr(item, "start_time", "")),
        )
        if not runs:
            return []

        def activity_day(item: Any) -> date | None:
            try:
                return datetime.fromisoformat(
                    str(getattr(item, "start_time", "")).replace("Z", "+00:00")
                ).date()
            except (TypeError, ValueError):
                return None

        dated = [(activity_day(item), item) for item in runs]
        dated = [(day, item) for day, item in dated if day is not None]
        if not dated:
            return []

        first_day, last_day = dated[0][0], dated[-1][0]
        cursor = min(last_day, first_day + timedelta(days=41))
        endpoints = []
        while cursor < last_day:
            endpoints.append(cursor)
            cursor += timedelta(days=7)
        endpoints.append(last_day)

        maximum_hr = profile.get("maximum_heart_rate_bpm")
        result = []
        for endpoint in endpoints:
            start = endpoint - timedelta(days=41)
            window = [item for day, item in dated if start <= day <= endpoint]
            estimate = ContinuousPhysiologyEstimator().estimate(
                window,
                {"maximum_heart_rate_bpm": maximum_hr},
            )
            if not estimate.get("updated"):
                continue
            sv1 = estimate.get("sv1") or {}
            sv2 = estimate.get("sv2") or {}
            observed_maximum_hr = max(
                (
                    float(getattr(item, "maximum_heart_rate_bpm"))
                    for item in window
                    if getattr(item, "maximum_heart_rate_bpm", None) is not None
                    and 100 <= float(getattr(item, "maximum_heart_rate_bpm")) <= 230
                ),
                default=maximum_hr,
            )
            result.append({
                "day": endpoint.isoformat(),
                "source": "historical_fit",
                "schema": "atlas_retrospective_v1",
                "method": "tendance terrain hebdomadaire sur 42 jours, recalée sur la référence actuelle",
                "vo2_max": estimate.get("vo2_max"),
                "vma_kmh": estimate.get("vma_kmh"),
                "sv1_speed_kmh": sv1.get("speed_kmh"),
                "sv2_speed_kmh": sv2.get("speed_kmh"),
                "maximum_heart_rate_bpm": maximum_hr,
                "observed_maximum_heart_rate_bpm": observed_maximum_hr,
                "estimator_confidence": estimate.get("confidence"),
                "evidence_sessions": estimate.get("evidence_sessions"),
            })

        sv1_profile = profile.get("sv1") or {}
        sv2_profile = profile.get("sv2") or {}
        targets = {
            "vo2_max": profile.get("vo2_max"),
            "vma_kmh": (
                profile.get("vma_estimated_from_vo2_kmh")
                or profile.get("vma_kmh")
                or profile.get("vma_training_reference_kmh")
            ),
            "sv1_speed_kmh": sv1_profile.get("speed_kmh"),
            "sv2_speed_kmh": sv2_profile.get("speed_kmh"),
            "maximum_heart_rate_bpm": maximum_hr,
        }
        bounds = {
            "vo2_max": (20, 90, 1),
            "vma_kmh": (6, 30, 2),
            "sv1_speed_kmh": (5, 24, 2),
            "sv2_speed_kmh": (6, 28, 2),
            "maximum_heart_rate_bpm": (100, 230, 0),
        }
        for field, target in targets.items():
            values = [item.get(field) for item in result if item.get(field) is not None]
            if target is None or not values:
                continue
            offset = float(target) - float(values[-1])
            minimum, maximum, digits = bounds[field]
            for item in result:
                if item.get(field) is not None:
                    item[field] = round(
                        max(minimum, min(maximum, float(item[field]) + offset)),
                        digits,
                    )
        return result

    @staticmethod
    def _action(score: Any) -> dict[str, Any]:
        if score is None:
            return {"level": "unknown", "decision": "keep", "reason": "Données quotidiennes insuffisantes."}
        if score >= 70:
            return {"level": "green", "decision": "keep", "reason": "Récupération compatible avec la séance prévue."}
        if score >= 45:
            return {"level": "orange", "decision": "reduce_specific_volume_25_percent",
                    "reason": "Récupération intermédiaire : réduction proposée du volume spécifique."}
        return {"level": "red", "decision": "replace_with_easy_endurance",
                "reason": "Récupération faible : endurance facile proposée à la place de l'intensité."}

    def _program_proposal(self, profile: dict[str, Any], action: dict[str, Any], score: Any,
                          estimate: dict[str, Any], nutrition: dict[str, Any]) -> dict[str, Any] | None:
        program = self._read("training-program.json", None)
        if not isinstance(program, dict):
            return None
        candidate = deepcopy(program)
        candidate["athlete_snapshot"] = {**candidate.get("athlete_snapshot", {}), **profile}
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "requires_user_validation": True,
            "active_program_unchanged": True,
            "reason": action["reason"],
            "recovery_index": score,
            "daily_action": action,
            "physiology_update": estimate,
            "nutrition_hydration_context": nutrition,
            "candidate_program": candidate,
        }

    def _merged_wellness(self) -> list[dict[str, Any]]:
        """Complète Santé Connect avec les journées Garmin absentes."""
        wellness = self._read("health-connect-wellness.json", [])
        merged = [
            dict(item) for item in wellness
            if isinstance(item, dict)
        ]
        sleep_days = {
            stamp.date().isoformat()
            for item in merged if item.get("type") == "sleep"
            for stamp in [self._timestamp(item.get("end_time"))]
            if stamp is not None
        }
        metric_keys = {
            (
                str(item.get("type") or ""),
                stamp.date().isoformat(),
            )
            for item in merged
            for stamp in [self._timestamp(item.get("start_time"))]
            if stamp is not None
        }
        cache = self._read("garmin-wellness-snapshot-cache.json", {})
        for archive in (cache.get("archives") or {}).values():
            snapshot = (
                archive.get("snapshot")
                if isinstance(archive, dict) else None
            )
            if not isinstance(snapshot, dict):
                continue
            day = str(snapshot.get("day") or "")[:10]
            if not day:
                continue
            end = datetime.fromisoformat(
                f"{day}T06:00:00+00:00"
            )
            duration_minutes = snapshot.get("sleep_duration_minutes")
            if day not in sleep_days and duration_minutes:
                start = end - timedelta(minutes=float(duration_minutes))
                merged.append({
                    "type": "sleep",
                    "source_id": f"garmin-wellness-sleep-{day}",
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "stages": [],
                    "source": "garmin_wellness",
                })
                sleep_days.add(day)
            for kind, field in (
                ("resting_heart_rate", "resting_heart_rate_bpm"),
                ("hrv_rmssd", "hrv_last_night_ms"),
            ):
                value = snapshot.get(field)
                if value is None or (kind, day) in metric_keys:
                    continue
                merged.append({
                    "type": kind,
                    "source_id": f"garmin-wellness-{kind}-{day}",
                    "start_time": end.isoformat(),
                    "value": value,
                    "source": "garmin_wellness",
                })
                metric_keys.add((kind, day))
        return merged

    @staticmethod
    def _timestamp(value: Any) -> datetime | None:
        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            return None

    def _current_physiology(self) -> dict[str, Any]:
        saved = self._read("physiology-longitudinal.json", {}).get("current")
        saved = saved if isinstance(saved, dict) else {}
        program = self._read("training-program.json", {})
        snapshot = program.get("athlete_snapshot") if isinstance(program, dict) else None
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        # La référence active affichée dans Atlas Coach reste l'ancre officielle.
        # Les estimations continues complètent les champs absents sans l'écraser.
        return {**saved, **snapshot}

    def _read(self, name: str, default: Any) -> Any:
        path = self.private_dir / name
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, name: str, value: Any) -> None:
        path = self.private_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=self._json_default,
            ) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        raise TypeError(
            f"Type non sérialisable : {type(value).__name__}"
        )
