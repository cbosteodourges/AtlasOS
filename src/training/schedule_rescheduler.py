"""Réorganisation prudente d'une semaine après déplacement utilisateur."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any


HARD_MARKERS = (
    "vo2", "vma", "interval", "threshold", "seuil", "sv2",
    "tempo", "long", "hybrid", "race", "competition",
)


def _day(value: Any) -> date:
    return date.fromisoformat(str(value or "")[:10])


def _is_hard(workout: dict[str, Any]) -> bool:
    text = " ".join(
        str(workout.get(field) or "").lower()
        for field in ("title", "workout_type", "session_type", "kind", "priority")
    )
    if any(marker in text for marker in HARD_MARKERS):
        return True
    return any(
        str(block.get("block_type") or "").lower()
        in {"interval", "threshold", "race", "tempo"}
        for block in workout.get("blocks") or []
    )


def _week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _workouts(program: dict[str, Any]):
    for week_index, week in enumerate(program.get("weeks") or []):
        for workout_index, workout in enumerate(week.get("workouts") or []):
            yield week_index, workout_index, workout


def _nearest_safe_day(
    preferred: date,
    start: date,
    end: date,
    occupied_hard: set[date],
) -> date | None:
    candidates = sorted(
        (start + timedelta(days=offset) for offset in range(7)),
        key=lambda candidate: (
            abs((candidate - preferred).days),
            candidate < preferred,
            candidate,
        ),
    )
    for candidate in candidates:
        if candidate in occupied_hard:
            continue
        if any(abs((candidate - other).days) < 2 for other in occupied_hard):
            continue
        return candidate
    return None


def reschedule_workout(
    program: dict[str, Any],
    workout_id: str,
    target_date: str,
) -> dict[str, Any]:
    """Retourne un programme candidat et une explication des changements.

    Le déplacement demandé reste prioritaire. Les autres séances difficiles de
    la même semaine sont décalées au jour libre le plus proche afin de conserver
    au moins une journée sans séance difficile entre deux stimuli importants.
    """

    candidate = deepcopy(program)
    target = _day(target_date)
    located = [item for item in _workouts(candidate) if str(item[2].get("workout_id")) == workout_id]
    if not located:
        raise ValueError("Séance introuvable dans le programme actif.")
    if len(located) > 1:
        raise ValueError("Identifiant de séance ambigu dans le programme actif.")

    source_week_index, _, selected = located[0]
    source = _day(selected.get("workout_date"))
    week_start, week_end = _week_bounds(source)
    if not week_start <= target <= week_end:
        raise ValueError("Le déplacement doit rester dans la même semaine d’entraînement.")

    changes = []
    selected["workout_date"] = target.isoformat()
    selected["rescheduled_from"] = source.isoformat()
    selected["rescheduled_by"] = "user"
    changes.append({
        "workout_id": workout_id,
        "title": selected.get("title") or "Séance",
        "from": source.isoformat(),
        "to": target.isoformat(),
        "reason": "Déplacement demandé par l’utilisateur.",
    })

    same_week = [
        workout for _, _, workout in _workouts(candidate)
        if week_start <= _day(workout.get("workout_date")) <= week_end
    ]
    hard = [workout for workout in same_week if _is_hard(workout)]
    hard.sort(key=lambda workout: (workout is not selected, _day(workout.get("workout_date"))))
    occupied = {target} if _is_hard(selected) else set()

    for workout in hard:
        if workout is selected:
            continue
        current = _day(workout.get("workout_date"))
        if all(abs((current - other).days) >= 2 for other in occupied):
            occupied.add(current)
            continue
        replacement = _nearest_safe_day(current, week_start, week_end, occupied)
        if replacement is None:
            raise ValueError(
                "Cette semaine ne permet pas de conserver un espacement sûr entre les séances difficiles."
            )
        workout["workout_date"] = replacement.isoformat()
        workout["rescheduled_from"] = current.isoformat()
        workout["rescheduled_by"] = "atlas_coherence"
        occupied.add(replacement)
        changes.append({
            "workout_id": workout.get("workout_id"),
            "title": workout.get("title") or "Séance",
            "from": current.isoformat(),
            "to": replacement.isoformat(),
            "reason": "Atlas préserve une journée sans séance difficile entre deux charges importantes.",
        })

    # Conserve le classement chronologique utilisé par le calendrier.
    candidate["weeks"][source_week_index]["workouts"].sort(
        key=lambda workout: (str(workout.get("workout_date") or ""), str(workout.get("workout_id") or ""))
    )
    return {
        "program": candidate,
        "changes": changes,
        "summary": (
            "Séance déplacée et semaine rééquilibrée automatiquement."
            if len(changes) > 1
            else "Séance déplacée sans autre modification nécessaire."
        ),
        "requires_confirmation": True,
    }
