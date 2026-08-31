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


def _program_week_bounds(week: dict[str, Any]) -> tuple[date, date]:
    """Retourne les limites réelles d'une semaine du programme."""

    start_value = week.get("start_date")
    end_value = week.get("end_date")
    if start_value and end_value:
        return _day(start_value), _day(end_value)

    workout_dates = [
        _day(workout.get("workout_date"))
        for workout in week.get("workouts") or []
        if workout.get("workout_date")
    ]
    if not workout_dates:
        raise ValueError("Une semaine du programme ne possède aucune date.")

    return _week_bounds(min(workout_dates))


def reschedule_workout(
    program: dict[str, Any],
    workout_id: str,
    target_date: str,
    rebalance: bool = True,
    replace_target_easy: bool = False,
) -> dict[str, Any]:
    """Déplace une séance dans le programme et préserve les récupérations."""

    candidate = deepcopy(program)
    target = _day(target_date)

    located = [
        item for item in _workouts(candidate)
        if str(item[2].get("workout_id")) == workout_id
    ]
    if not located:
        raise ValueError("Séance introuvable dans le programme actif.")
    if len(located) > 1:
        raise ValueError(
            "Identifiant de séance ambigu dans le programme actif."
        )

    source_week_index, source_workout_index, selected = located[0]
    source = _day(selected.get("workout_date"))

    matching_weeks = []
    for week_index, week in enumerate(candidate.get("weeks") or []):
        week_start, week_end = _program_week_bounds(week)
        if week_start <= target <= week_end:
            matching_weeks.append((week_index, week_start, week_end))

    if not matching_weeks:
        raise ValueError(
            "La nouvelle date doit appartenir à une semaine "
            "du programme actif."
        )
    if len(matching_weeks) > 1:
        raise ValueError(
            "La nouvelle date correspond à plusieurs semaines du programme."
        )

    target_week_index, _, _ = matching_weeks[0]
    changes = []

    source_workouts = candidate["weeks"][source_week_index]["workouts"]
    source_workouts.pop(source_workout_index)

    selected["workout_date"] = target.isoformat()
    selected["rescheduled_from"] = source.isoformat()
    selected["rescheduled_by"] = "user"
    candidate["weeks"][target_week_index].setdefault(
        "workouts", []
    ).append(selected)

    target_conflicts = [
        {
            "workout_id": workout.get("workout_id"),
            "title": workout.get("title") or "Séance",
            "workout_type": workout.get("workout_type"),
            "is_hard": _is_hard(workout),
        }
        for _, _, workout in _workouts(candidate)
        if (
            workout is not selected
            and _day(workout.get("workout_date")) == target
        )
    ]

    removed_workouts = []
    if replace_target_easy:
        for week in candidate.get("weeks") or []:
            kept = []
            for workout in week.get("workouts") or []:
                same_target = (
                    workout is not selected
                    and _day(workout.get("workout_date")) == target
                )
                if same_target and not _is_hard(workout):
                    removed_workouts.append({
                        "workout_id": workout.get("workout_id"),
                        "title": workout.get("title") or "Séance",
                        "workout_date": workout.get("workout_date"),
                        "reason": (
                            "Séance facile remplacée à la demande "
                            "de l’utilisateur."
                        ),
                    })
                    continue
                kept.append(workout)
            week["workouts"] = kept

    changes.append({
        "workout_id": workout_id,
        "title": selected.get("title") or "Séance",
        "from": source.isoformat(),
        "to": target.isoformat(),
        "reason": "Déplacement demandé par l’utilisateur.",
    })

    # La séance demandée reste prioritaire. Les autres séances difficiles
    # sont contrôlées dans tout le programme afin de protéger également
    # la frontière entre deux semaines.
    occupied_hard = {target} if _is_hard(selected) else set()
    other_hard = [
        (week_index, workout)
        for week_index, _, workout in _workouts(candidate)
        if (
            rebalance
            and workout is not selected
            and _is_hard(workout)
        )
    ]
    other_hard.sort(
        key=lambda item: (
            _day(item[1].get("workout_date")),
            str(item[1].get("workout_id") or ""),
        )
    )

    for week_index, workout in other_hard:
        current = _day(workout.get("workout_date"))

        if all(
            abs((current - other).days) >= 2
            for other in occupied_hard
        ):
            occupied_hard.add(current)
            continue

        week_start, week_end = _program_week_bounds(
            candidate["weeks"][week_index]
        )
        replacement = _nearest_safe_day(
            current,
            week_start,
            week_end,
            occupied_hard,
        )
        if replacement is None:
            raise ValueError(
                "Le programme ne permet pas de conserver un espacement "
                "sûr entre les séances difficiles."
            )

        workout["workout_date"] = replacement.isoformat()
        workout["rescheduled_from"] = current.isoformat()
        workout["rescheduled_by"] = "atlas_coherence"
        occupied_hard.add(replacement)

        changes.append({
            "workout_id": workout.get("workout_id"),
            "title": workout.get("title") or "Séance",
            "from": current.isoformat(),
            "to": replacement.isoformat(),
            "reason": (
                "Atlas préserve une journée sans séance difficile "
                "entre deux charges importantes."
            ),
        })

    for week in candidate.get("weeks") or []:
        week.setdefault("workouts", []).sort(
            key=lambda workout: (
                str(workout.get("workout_date") or ""),
                str(workout.get("workout_id") or ""),
            )
        )

    crossed_week = source_week_index != target_week_index
    return {
        "program": candidate,
        "changes": changes,
        "target_conflicts": target_conflicts,
        "removed_workouts": removed_workouts,
        "summary": (
            "Séance déplacée et séance facile du jour remplacée."
            if removed_workouts
            else
            "Séance déplacée uniquement, selon le choix de l’utilisateur."
            if not rebalance
            else "Séance reportée dans une autre semaine et programme "
            "rééquilibré automatiquement."
            if crossed_week
            else "Séance déplacée et programme rééquilibré automatiquement."
            if len(changes) > 1
            else "Séance déplacée sans autre modification nécessaire."
        ),
        "requires_confirmation": True,
    }
