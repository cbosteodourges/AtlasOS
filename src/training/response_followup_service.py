"""Construction automatique des suivis de réponse à 24–72 heures."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .response_learning import (
    TrainingResponseLearningEngine,
    TrainingResponseObservation,
)


class TrainingResponseFollowupService:
    """Relie exécutions, Wellness et ressenti sans inventer de mesure."""

    CHECKPOINTS = (24, 48, 72)
    MAX_CHECKPOINT_DISTANCE_HOURS = 10

    def build(
        self,
        workouts: list[Any],
        executions: list[dict[str, Any]],
        recovery_history: list[dict[str, Any]],
        contexts: list[dict[str, Any]],
        *,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = now or datetime.now(timezone.utc)
        by_id = {item.workout_id: item for item in workouts}
        context_by_workout = {
            str(item.get("workout_id") or ""): item
            for item in contexts if isinstance(item, dict)
        }
        recovery = sorted(
            (item for item in recovery_history if isinstance(item, dict)),
            key=lambda item: str(item.get("day") or item.get("timestamp") or ""),
        )
        results: list[dict[str, Any]] = []

        for execution in executions:
            workout_id = self._workout_id(execution)
            workout = by_id.get(workout_id)
            occurred_at = self._timestamp(
                execution.get("start_time") or execution.get("activity", {}).get("start_time")
            )
            if workout is None or occurred_at is None:
                continue
            age_hours = (now - occurred_at).total_seconds() / 3600
            if age_hours < 24:
                continue

            baseline = self._baseline(recovery, occurred_at)
            observations = self._observations(
                workout_id, occurred_at, recovery,
                context_by_workout.get(workout_id, {}), now,
            )
            learning = TrainingResponseLearningEngine().analyze(
                workout,
                observations,
                pre_session_recovery_score=self._number(
                    baseline, "recovery_score", "atlas_recovery_index"
                ),
                pre_session_atlas_index_score=self._number(
                    baseline, "atlas_index", "atlas_recovery_index"
                ),
                pre_session_pain_0_10=self._number(
                    context_by_workout.get(workout_id, {}), "pain_before_0_to_10"
                ),
            )
            results.append({
                "workout_id": workout_id,
                "workout_type": workout.workout_type.value,
                "session_started_at": occurred_at.isoformat(),
                "evaluated_at": now.isoformat(),
                "checkpoints": [asdict(item) for item in observations],
                "learning": learning.to_dict(),
                "next_decision_context": {
                    "load_factor": learning.next_load_factor,
                    "usable": learning.usable_for_learning,
                    "reason": learning.reasons[-1] if learning.reasons else "",
                    "alerts": learning.alerts,
                },
            })
        return sorted(results, key=lambda item: item["session_started_at"])

    def _observations(self, workout_id, started, history, context, now):
        observations = []
        for checkpoint in self.CHECKPOINTS:
            if (now - started).total_seconds() < checkpoint * 3600:
                continue
            target = started.timestamp() + checkpoint * 3600
            candidates = []
            for item in history:
                stamp = self._timestamp(item.get("timestamp") or item.get("day"))
                if stamp is not None:
                    candidates.append((abs(stamp.timestamp() - target), item))
            if not candidates:
                continue
            distance, item = min(candidates, key=lambda pair: pair[0])
            if distance > self.MAX_CHECKPOINT_DISTANCE_HOURS * 3600:
                continue
            observations.append(TrainingResponseObservation(
                workout_id=workout_id,
                hours_after_session=checkpoint,
                recovery_score=self._number(item, "recovery_score", "atlas_recovery_index"),
                atlas_index_score=self._number(item, "atlas_index", "atlas_recovery_index"),
                hrv_ms=self._number(item, "hrv_last_night_ms", "hrv_ms"),
                resting_heart_rate_bpm=self._number(item, "resting_heart_rate_bpm"),
                sleep_score=self._number(item, "sleep_score", "sleep_quality_score"),
                fatigue_0_10=self._number(context, "fatigue_0_to_10"),
                muscle_soreness_0_10=self._number(context, "muscle_soreness_0_to_10"),
                pain_0_10=self._number(context, "pain_0_to_10"),
                illness_symptoms=bool(context.get("illness_symptoms", False)),
                workout_completed=True,
                actual_rpe_0_10=self._number(context, "perceived_effort_0_to_10"),
                notes=str(context.get("comment") or ""),
            ))
        return observations

    def _baseline(self, history, started):
        candidates = []
        for item in history:
            stamp = self._timestamp(item.get("timestamp") or item.get("day"))
            if stamp is not None and stamp <= started:
                candidates.append((stamp, item))
        return max(candidates, key=lambda pair: pair[0])[1] if candidates else {}

    @staticmethod
    def _workout_id(execution):
        match = execution.get("atlas_workout_match") or execution.get("workout_match") or {}
        return str(match.get("workout_id") or execution.get("workout_id") or "")

    @staticmethod
    def _timestamp(value):
        if not value:
            return None
        try:
            raw = str(value)
            if len(raw) == 10:
                raw += "T12:00:00+00:00"
            result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if result.tzinfo is None:
                result = result.replace(tzinfo=timezone.utc)
            return result.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _number(source, *keys):
        for key in keys:
            value = source.get(key) if isinstance(source, dict) else None
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
        return None
