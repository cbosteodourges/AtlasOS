"""
ATLAS OS
Application concrète d’une décision à une séance planifiée.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import timedelta

from .decision_engine import (
    TrainingDecision,
    TrainingDecisionAction,
)
from .session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    IntensityTarget,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


@dataclass(slots=True)
class AdaptedWorkoutResult:
    """Séance adaptée avec traçabilité des modifications."""

    original_workout: AdaptiveWorkout
    adapted_workout: AdaptiveWorkout
    decision: TrainingDecision
    modifications: list[str] = field(
        default_factory=list
    )


class WorkoutAdaptationEngine:
    """Transforme une décision en séance réellement exécutable."""

    def adapt(
        self,
        workout: AdaptiveWorkout,
        decision: TrainingDecision,
    ) -> AdaptedWorkoutResult:
        """Applique la décision sans modifier la séance originale."""
        workout.validate()

        if decision.workout_id != workout.workout_id:
            raise ValueError(
                "La décision ne correspond pas à la séance."
            )

        original = deepcopy(workout)

        if decision.action == TrainingDecisionAction.MAINTAIN:
            return AdaptedWorkoutResult(
                original_workout=original,
                adapted_workout=deepcopy(workout),
                decision=decision,
                modifications=[
                    "Séance maintenue sans modification."
                ],
            )

        if decision.action == TrainingDecisionAction.REDUCE:
            adapted, modifications = self._reduce(
                workout,
                decision,
            )
        elif decision.action == TrainingDecisionAction.REPLACE:
            adapted, modifications = self._replace(
                workout,
                decision,
            )
        elif decision.action == TrainingDecisionAction.POSTPONE:
            adapted, modifications = self._postpone(
                workout,
                decision,
            )
        elif decision.action == TrainingDecisionAction.CANCEL:
            adapted, modifications = self._cancel(
                workout,
            )
        else:
            raise ValueError(
                f"Décision non prise en charge : {decision.action}"
            )

        adapted.validate()

        return AdaptedWorkoutResult(
            original_workout=original,
            adapted_workout=adapted,
            decision=decision,
            modifications=modifications,
        )

    def _reduce(
        self,
        workout: AdaptiveWorkout,
        decision: TrainingDecision,
    ) -> tuple[AdaptiveWorkout, list[str]]:
        adapted = deepcopy(workout)
        modifications: list[str] = []

        adapted.title = f"{workout.title} — adaptée"
        adapted.coach_notes.append(
            "Séance allégée automatiquement par Atlas Coach."
        )

        for block in adapted.blocks:
            if block.block_type in {
                BlockType.WARM_UP,
                BlockType.COOL_DOWN,
                BlockType.RECOVERY,
                BlockType.MOBILITY,
            }:
                continue

            if block.repetitions > 1:
                original_repetitions = block.repetitions
                block.repetitions = max(
                    1,
                    int(
                        block.repetitions
                        * decision.duration_factor
                    ),
                )

                if (
                    block.repetitions
                    != original_repetitions
                ):
                    modifications.append(
                        f"{block.name} : "
                        f"{original_repetitions} répétitions "
                        f"réduites à {block.repetitions}."
                    )
            elif block.duration_minutes is not None:
                original_duration = block.duration_minutes
                block.duration_minutes = max(
                    5.0,
                    round(
                        block.duration_minutes
                        * decision.duration_factor,
                        1,
                    ),
                )

                if (
                    block.duration_minutes
                    != original_duration
                ):
                    modifications.append(
                        f"{block.name} : durée réduite de "
                        f"{original_duration:g} à "
                        f"{block.duration_minutes:g} minutes."
                    )

            if block.target.rpe_0_10 is not None:
                original_rpe = block.target.rpe_0_10
                block.target.rpe_0_10 = round(
                    original_rpe
                    * decision.intensity_factor,
                    1,
                )
                modifications.append(
                    f"{block.name} : RPE cible réduite de "
                    f"{original_rpe:g} à "
                    f"{block.target.rpe_0_10:g}/10."
                )

        if adapted.planned_duration_minutes is not None:
            adapted.planned_duration_minutes = round(
                adapted.planned_duration_minutes
                * decision.duration_factor
            )

        if adapted.planned_distance_km is not None:
            adapted.planned_distance_km = round(
                adapted.planned_distance_km
                * decision.duration_factor,
                1,
            )

        if adapted.expected_response is not None:
            response = adapted.expected_response
            response.physiological_load_0_100 = round(
                response.physiological_load_0_100
                * decision.duration_factor
                * decision.intensity_factor
            )
            response.biomechanical_load_0_100 = round(
                response.biomechanical_load_0_100
                * decision.duration_factor
            )
            response.recovery_min_hours = round(
                response.recovery_min_hours
                * decision.duration_factor
            )
            response.recovery_max_hours = round(
                response.recovery_max_hours
                * decision.duration_factor
            )

        if not modifications:
            modifications.append(
                "Charge globale réduite sans altérer "
                "la structure principale."
            )

        return adapted, modifications

    def _replace(
        self,
        workout: AdaptiveWorkout,
        decision: TrainingDecision,
    ) -> tuple[AdaptiveWorkout, list[str]]:
        replacement_type = (
            decision.replacement_type
            or WorkoutType.ENDURANCE_Z2
        )

        if replacement_type == WorkoutType.REST:
            return self._cancel(workout)

        original_duration = (
            workout.estimated_duration_minutes
        )
        replacement_duration = max(
            25,
            round(
                original_duration
                * decision.duration_factor
            ),
        )
        warm_up_duration = min(
            10,
            max(5, round(replacement_duration * 0.20)),
        )
        cool_down_duration = min(
            5,
            max(3, round(replacement_duration * 0.10)),
        )
        continuous_duration = max(
            15,
            replacement_duration
            - warm_up_duration
            - cool_down_duration,
        )

        adapted = AdaptiveWorkout(
            workout_id=workout.workout_id,
            workout_date=workout.workout_date,
            workout_type=replacement_type,
            title="Endurance facile de substitution",
            objective=(
                "Entretenir l’adaptation aérobie sans ajouter "
                "une fatigue excessive."
            ),
            sport=workout.sport,
            priority=WorkoutPriority.SUPPORT,
            blocks=[
                TrainingBlock(
                    name="Mise en route",
                    block_type=BlockType.WARM_UP,
                    duration_minutes=warm_up_duration,
                    target=IntensityTarget(
                        zone=1,
                        rpe_0_10=2,
                    ),
                ),
                TrainingBlock(
                    name="Endurance facile",
                    block_type=BlockType.CONTINUOUS,
                    duration_minutes=continuous_duration,
                    target=IntensityTarget(
                        zone=2,
                        rpe_0_10=3,
                    ),
                    instructions=(
                        "Rester en aisance respiratoire."
                    ),
                ),
                TrainingBlock(
                    name="Retour au calme",
                    block_type=BlockType.COOL_DOWN,
                    duration_minutes=cool_down_duration,
                    target=IntensityTarget(
                        zone=1,
                        rpe_0_10=2,
                    ),
                ),
            ],
            planned_duration_minutes=replacement_duration,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=35,
                biomechanical_load_0_100=30,
                recovery_min_hours=12,
                recovery_max_hours=24,
                sensitive_structures=(
                    list(
                        workout.expected_response
                        .sensitive_structures
                    )
                    if workout.expected_response is not None
                    else []
                ),
            ),
            movable=False,
            maximum_shift_days=0,
            replacement_types=[],
            coach_notes=[
                "Séance de substitution générée par Atlas Coach."
            ],
        )

        return adapted, [
            f"{workout.title} remplacée par "
            f"{adapted.title}.",
            f"Durée adaptée à {replacement_duration} minutes.",
        ]

    @staticmethod
    def _postpone(
        workout: AdaptiveWorkout,
        decision: TrainingDecision,
    ) -> tuple[AdaptiveWorkout, list[str]]:
        adapted = deepcopy(workout)
        original_date = adapted.workout_date
        adapted.workout_date = (
            adapted.workout_date
            + timedelta(days=decision.shift_days)
        )
        adapted.coach_notes.append(
            "Séance reportée par Atlas Coach."
        )

        return adapted, [
            f"Séance reportée du {original_date.isoformat()} "
            f"au {adapted.workout_date.isoformat()}."
        ]

    @staticmethod
    def _cancel(
        workout: AdaptiveWorkout,
    ) -> tuple[AdaptiveWorkout, list[str]]:
        adapted = AdaptiveWorkout(
            workout_id=workout.workout_id,
            workout_date=workout.workout_date,
            workout_type=WorkoutType.REST,
            title="Récupération complète",
            objective=(
                "Permettre la récupération avant "
                "une nouvelle réévaluation."
            ),
            sport=workout.sport,
            priority=WorkoutPriority.SUPPORT,
            blocks=[],
            planned_duration_minutes=0,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=0,
                biomechanical_load_0_100=0,
                recovery_min_hours=0,
                recovery_max_hours=24,
            ),
            movable=False,
            maximum_shift_days=0,
            replacement_types=[],
            coach_notes=[
                "Repos décidé par Atlas Coach."
            ],
        )

        return adapted, [
            f"{workout.title} annulée.",
            "Une journée de récupération complète est proposée.",
        ]