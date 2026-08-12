"""
ATLAS OS
Décisions utilisateur sur les séances planifiées.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

from .decision_engine import TrainingDecisionAction
from .session_models import AdaptiveWorkout, WorkoutPriority


class UserWorkoutStatus(str, Enum):
    """État déclaré ou détecté d'une séance."""

    PLANNED = "planned"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    POSTPONED = "postponed"
    REPLACED = "replaced"
    MODIFIED = "modified"


@dataclass(slots=True)
class UserWorkoutScheduleDecision:
    """Impact explicable d'une décision utilisateur."""

    workout_id: str
    status: UserWorkoutStatus
    action: TrainingDecisionAction
    recalculate_future_program: bool

    removed_duration_minutes: int = 0
    removed_physiological_load: int = 0
    removed_biomechanical_load: int = 0
    shift_days: int = 0
    reason: str = ""
    explanations: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["status"] = self.status.value
        result["action"] = self.action.value
        result["explanations"] = list(self.explanations or [])
        return result


class UserWorkoutDecisionEngine:
    """Traduit un choix utilisateur en impact sur le programme."""

    def skip(
        self,
        workout: AdaptiveWorkout,
        *,
        reason: str = "",
        sessions_on_next_day: int = 0,
    ) -> UserWorkoutScheduleDecision:
        """Analyse une séance que l'utilisateur ne réalisera pas."""

        workout.validate()
        response = workout.expected_response
        duration = int(workout.planned_duration_minutes or 0)
        physiological_load = (
            response.physiological_load_0_100
            if response is not None
            else 0
        )
        biomechanical_load = (
            response.biomechanical_load_0_100
            if response is not None
            else 0
        )

        explanations = [
            "La séance est enregistrée comme non effectuée.",
            (
                f"{duration} min, {physiological_load} points "
                "physiologiques et "
                f"{biomechanical_load} points biomécaniques "
                "sont retirés de la charge réellement accomplie."
            ),
        ]

        if workout.priority in {
            WorkoutPriority.SUPPORT,
            WorkoutPriority.OPTIONAL,
        }:
            explanations.append(
                "Une séance complémentaire n'est pas reportée "
                "automatiquement."
            )
            if sessions_on_next_day >= 2:
                explanations.append(
                    "Le lendemain comporte déjà deux séances : "
                    "aucune charge supplémentaire n'est ajoutée."
                )

            return UserWorkoutScheduleDecision(
                workout_id=workout.workout_id,
                status=UserWorkoutStatus.SKIPPED,
                action=TrainingDecisionAction.CANCEL,
                recalculate_future_program=False,
                removed_duration_minutes=duration,
                removed_physiological_load=physiological_load,
                removed_biomechanical_load=biomechanical_load,
                reason=reason.strip(),
                explanations=explanations,
            )

        explanations.append(
            "La séance est prioritaire : Atlas doit rechercher "
            "un report ou un remplacement compatible."
        )

        return UserWorkoutScheduleDecision(
            workout_id=workout.workout_id,
            status=UserWorkoutStatus.SKIPPED,
            action=TrainingDecisionAction.POSTPONE,
            recalculate_future_program=True,
            removed_duration_minutes=duration,
            removed_physiological_load=physiological_load,
            removed_biomechanical_load=biomechanical_load,
            shift_days=1 if workout.movable else 0,
            reason=reason.strip(),
            explanations=explanations,
        )