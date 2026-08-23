"""Contrôle de cohérence entre programme actif et historique Atlas."""

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class PlanHistoryAudit:
    planned_workouts: int
    past_workouts: int
    completed_past_workouts: int
    missing_past_workout_ids: List[str]
    duplicate_execution_workout_ids: List[str]
    orphan_execution_ids: List[str]

    @property
    def is_consistent(self) -> bool:
        return not (
            self.missing_past_workout_ids
            or self.duplicate_execution_workout_ids
            or self.orphan_execution_ids
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["is_consistent"] = self.is_consistent
        return payload


def _workout_id(item: Dict[str, Any]) -> str:
    return str(item.get("workout_id") or item.get("id") or "").strip()


def _execution_workout_id(item: Dict[str, Any]) -> str:
    planned = item.get("planned_workout") or {}
    match = item.get("match") or {}
    return str(
        planned.get("workout_id")
        or planned.get("id")
        or match.get("workout_id")
        or item.get("workout_id")
        or ""
    ).strip()


def _execution_id(item: Dict[str, Any]) -> str:
    activity = item.get("activity") or {}
    return str(
        item.get("execution_id")
        or activity.get("atlas_id")
        or activity.get("external_id")
        or "execution-sans-identifiant"
    )


def audit_plan_history(
    program: Dict[str, Any],
    executions: Iterable[Dict[str, Any]],
    today: date | None = None,
) -> PlanHistoryAudit:
    reference = today or date.today()
    workouts = [
        workout
        for week in program.get("weeks", [])
        for workout in (week.get("workouts") or [])
        if _workout_id(workout)
    ]
    known = {_workout_id(workout) for workout in workouts}
    past = {
        _workout_id(workout)
        for workout in workouts
        if workout.get("workout_date")
        and date.fromisoformat(str(workout["workout_date"])[:10]) < reference
        and not workout.get("optional", False)
    }

    counts: Dict[str, int] = {}
    orphan_ids: List[str] = []
    for execution in executions:
        workout_id = _execution_workout_id(execution)
        matched = bool((execution.get("match") or {}).get("matched", workout_id))
        if workout_id and matched:
            counts[workout_id] = counts.get(workout_id, 0) + 1
            if workout_id not in known:
                orphan_ids.append(_execution_id(execution))

    completed = past.intersection(counts)
    duplicates = sorted(key for key, count in counts.items() if count > 1 and key in known)
    return PlanHistoryAudit(
        planned_workouts=len(workouts),
        past_workouts=len(past),
        completed_past_workouts=len(completed),
        missing_past_workout_ids=sorted(past - completed),
        duplicate_execution_workout_ids=duplicates,
        orphan_execution_ids=sorted(set(orphan_ids)),
    )
