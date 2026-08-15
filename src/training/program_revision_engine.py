"""
ATLAS OS
Comparaison explicable des révisions du programme d'entraînement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class TrainingProgramChange:
    """Modification future détectée entre deux programmes."""

    workout_id: str
    workout_date: date
    change_type: str
    changed_fields: list[str] = field(default_factory=list)
    active_workout: dict[str, Any] | None = None
    candidate_workout: dict[str, Any] | None = None
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workout_id": self.workout_id,
            "workout_date": self.workout_date.isoformat(),
            "change_type": self.change_type,
            "changed_fields": list(self.changed_fields),
            "active_workout": self.active_workout,
            "candidate_workout": self.candidate_workout,
            "reasons": list(self.reasons),
        }


@dataclass(slots=True)
class TrainingProgramRevisionProposal:
    """Proposition Atlas nécessitant une validation explicite."""

    as_of: date
    status: str
    changes: list[TrainingProgramChange] = field(
        default_factory=list
    )
    requires_approval: bool = False
    automatically_applied: bool = False
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat(),
            "status": self.status,
            "changes": [
                change.to_dict()
                for change in self.changes
            ],
            "requires_approval": self.requires_approval,
            "automatically_applied": self.automatically_applied,
            "explanations": list(self.explanations),
        }


class TrainingProgramRevisionEngine:
    """Compare un programme actif à un candidat régénéré."""

    def compare(
        self,
        active_program: dict[str, Any],
        candidate_program: dict[str, Any],
        *,
        as_of: date,
    ) -> TrainingProgramRevisionProposal:
        active = self._future_workouts(
            active_program,
            as_of=as_of,
        )
        candidate = self._future_workouts(
            candidate_program,
            as_of=as_of,
        )
        changes: list[TrainingProgramChange] = []

        for workout_id in sorted(active.keys() | candidate.keys()):
            active_workout = active.get(workout_id)
            candidate_workout = candidate.get(workout_id)

            if active_workout is None:
                changes.append(
                    self._change(
                        workout_id,
                        "added",
                        None,
                        candidate_workout,
                    )
                )
                continue

            if candidate_workout is None:
                changes.append(
                    self._change(
                        workout_id,
                        "removed",
                        active_workout,
                        None,
                    )
                )
                continue

            changed_fields = sorted(
                field_name
                for field_name in (
                    active_workout.keys()
                    | candidate_workout.keys()
                )
                if active_workout.get(field_name)
                != candidate_workout.get(field_name)
            )

            if changed_fields:
                changes.append(
                    self._change(
                        workout_id,
                        "modified",
                        active_workout,
                        candidate_workout,
                        changed_fields=changed_fields,
                    )
                )

        if not changes:
            return TrainingProgramRevisionProposal(
                as_of=as_of,
                status="no_change",
                explanations=[
                    "Aucune séance future ne nécessite de révision."
                ],
            )

        return TrainingProgramRevisionProposal(
            as_of=as_of,
            status="proposed",
            changes=changes,
            requires_approval=True,
            automatically_applied=False,
            explanations=[
                (
                    f"{len(changes)} modification(s) future(s) "
                    "détectée(s)."
                ),
                (
                    "Les séances passées sont conservées et aucune "
                    "modification n'est appliquée sans validation."
                ),
            ],
        )

    @classmethod
    def _future_workouts(
        cls,
        program: dict[str, Any],
        *,
        as_of: date,
    ) -> dict[str, dict[str, Any]]:
        workouts: dict[str, dict[str, Any]] = {}

        for week in program.get("weeks", []):
            if not isinstance(week, dict):
                continue
            for workout in week.get("workouts", []):
                if not isinstance(workout, dict):
                    continue

                workout_id = str(workout.get("workout_id") or "")
                workout_date = cls._date(workout.get("workout_date"))

                if (
                    workout_id
                    and workout_date is not None
                    and workout_date >= as_of
                ):
                    workouts[workout_id] = workout

        return workouts

    @classmethod
    def _change(
        cls,
        workout_id: str,
        change_type: str,
        active_workout: dict[str, Any] | None,
        candidate_workout: dict[str, Any] | None,
        *,
        changed_fields: list[str] | None = None,
    ) -> TrainingProgramChange:
        reference = candidate_workout or active_workout or {}
        workout_date = cls._date(reference.get("workout_date"))

        if workout_date is None:
            raise ValueError(
                f"Date absente pour la séance {workout_id}."
            )

        return TrainingProgramChange(
            workout_id=workout_id,
            workout_date=workout_date,
            change_type=change_type,
            changed_fields=changed_fields or [],
            active_workout=active_workout,
            candidate_workout=candidate_workout,
            reasons=[
                (
                    "Révision issue des nouvelles données "
                    "FIT + Wellness."
                )
            ],
        )

    @staticmethod
    def _date(value: Any) -> date | None:
        if isinstance(value, date):
            return value
        if value is None:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None