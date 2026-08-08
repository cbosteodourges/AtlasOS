"""
ATLAS OS
Décision quotidienne appliquée à une séance planifiée.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

from src.atlas_brain.atlas_index import AtlasIndexResult

from .session_models import (
    AdaptiveWorkout,
    WorkoutPriority,
    WorkoutType,
)


class TrainingDecisionAction(str, Enum):
    """Actions possibles sur la séance du jour."""

    MAINTAIN = "maintain"
    REDUCE = "reduce"
    REPLACE = "replace"
    POSTPONE = "postpone"
    CANCEL = "cancel"


@dataclass(slots=True)
class TrainingDecision:
    """Décision explicable avant adaptation de la séance."""

    workout_id: str
    action: TrainingDecisionAction
    atlas_index_score: int
    session_demand_score: int
    compatibility_score: int

    duration_factor: float = 1.0
    intensity_factor: float = 1.0
    replacement_type: Optional[WorkoutType] = None
    shift_days: int = 0

    reasons: list[str] = field(default_factory=list)
    safety_alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["action"] = self.action.value
        result["replacement_type"] = (
            None
            if self.replacement_type is None
            else self.replacement_type.value
        )
        return result


class TrainingDecisionEngine:
    """Compare la capacité du jour à la demande de la séance."""

    INTENSE_TYPES = {
        WorkoutType.TEMPO_Z3,
        WorkoutType.THRESHOLD_SV2,
        WorkoutType.VMA_SHORT,
        WorkoutType.VMA_LONG,
        WorkoutType.RACE_SPECIFIC,
        WorkoutType.LONG_RUN,
    }

    def decide(
        self,
        atlas_index: AtlasIndexResult,
        workout: AdaptiveWorkout,
    ) -> TrainingDecision:
        """Décide de maintenir, adapter ou déplacer la séance."""
        workout.validate()

        demand = self._session_demand(workout)
        compatibility = self._compatibility(
            atlas_index,
            workout,
            demand,
        )
        reasons = [
            f"Indice ATLAS : {atlas_index.score}/100.",
            f"Demande prévue de la séance : {demand}/100.",
            f"Compatibilité du jour : {compatibility}/100.",
        ]

        if workout.workout_type == WorkoutType.REST:
            return self._result(
                workout,
                atlas_index,
                demand,
                compatibility,
                TrainingDecisionAction.MAINTAIN,
                reasons + [
                    "Le repos planifié est maintenu."
                ],
            )

        if atlas_index.alerts or atlas_index.score < 35:
            return self._result(
                workout,
                atlas_index,
                demand,
                compatibility,
                TrainingDecisionAction.CANCEL,
                reasons + [
                    "La sécurité et la récupération priment "
                    "sur le stimulus planifié."
                ],
                duration_factor=0.0,
                intensity_factor=0.0,
                replacement_type=WorkoutType.REST,
                safety_alerts=list(atlas_index.alerts),
            )

        if atlas_index.score < 55:
            if (
                workout.priority == WorkoutPriority.KEY
                and workout.movable
                and workout.maximum_shift_days >= 1
            ):
                return self._result(
                    workout,
                    atlas_index,
                    demand,
                    compatibility,
                    TrainingDecisionAction.POSTPONE,
                    reasons + [
                        "La séance clé est conservée mais "
                        "reportée pour éviter de perdre son objectif."
                    ],
                    duration_factor=0.0,
                    intensity_factor=0.0,
                    shift_days=1,
                )

            return self._replacement(
                workout,
                atlas_index,
                demand,
                compatibility,
                reasons + [
                    "La disponibilité du jour est insuffisante "
                    "pour la séance prévue."
                ],
            )

        high_demand = (
            workout.workout_type in self.INTENSE_TYPES
            or demand >= 65
        )

        if atlas_index.score < 65:
            if high_demand or compatibility < 55:
                return self._replacement(
                    workout,
                    atlas_index,
                    demand,
                    compatibility,
                    reasons + [
                        "Le stimulus prévu dépasse la capacité "
                        "disponible aujourd’hui."
                    ],
                )

            return self._reduction(
                workout,
                atlas_index,
                demand,
                compatibility,
                reasons + [
                    "La séance reste possible avec une réduction "
                    "nette du volume et de l’intensité."
                ],
                duration_factor=0.75,
                intensity_factor=0.85,
            )

        if atlas_index.score < 75:
            if high_demand or compatibility < 65:
                return self._reduction(
                    workout,
                    atlas_index,
                    demand,
                    compatibility,
                    reasons + [
                        "La séance exigeante est allégée afin de "
                        "préserver l’adaptation à 24–72 heures."
                    ],
                    duration_factor=0.85,
                    intensity_factor=0.90,
                )

        if compatibility < 60:
            return self._reduction(
                workout,
                atlas_index,
                demand,
                compatibility,
                reasons + [
                    "L’Indice ATLAS est favorable, mais la demande "
                    "spécifique de cette séance reste trop élevée."
                ],
                duration_factor=0.85,
                intensity_factor=0.90,
            )

        return self._result(
            workout,
            atlas_index,
            demand,
            compatibility,
            TrainingDecisionAction.MAINTAIN,
            reasons + [
                "La capacité du jour est compatible avec "
                "la séance planifiée."
            ],
        )

    def _replacement(
        self,
        workout: AdaptiveWorkout,
        atlas_index: AtlasIndexResult,
        demand: int,
        compatibility: int,
        reasons: list[str],
    ) -> TrainingDecision:
        replacement = (
            workout.replacement_types[0]
            if workout.replacement_types
            else WorkoutType.ENDURANCE_Z2
        )

        return self._result(
            workout,
            atlas_index,
            demand,
            compatibility,
            TrainingDecisionAction.REPLACE,
            reasons + [
                "La séance est remplacée par une option "
                f"moins exigeante : {replacement.value}."
            ],
            duration_factor=0.70,
            intensity_factor=0.75,
            replacement_type=replacement,
        )

    def _reduction(
        self,
        workout: AdaptiveWorkout,
        atlas_index: AtlasIndexResult,
        demand: int,
        compatibility: int,
        reasons: list[str],
        *,
        duration_factor: float,
        intensity_factor: float,
    ) -> TrainingDecision:
        return self._result(
            workout,
            atlas_index,
            demand,
            compatibility,
            TrainingDecisionAction.REDUCE,
            reasons,
            duration_factor=duration_factor,
            intensity_factor=intensity_factor,
        )

    @staticmethod
    def _session_demand(
        workout: AdaptiveWorkout,
    ) -> int:
        response = workout.expected_response

        if response is None:
            return 50

        return round(
            response.physiological_load_0_100 * 0.60
            + response.biomechanical_load_0_100 * 0.40
        )

    @staticmethod
    def _compatibility(
        atlas_index: AtlasIndexResult,
        workout: AdaptiveWorkout,
        demand: int,
    ) -> int:
        physiological_capacity = (
            atlas_index.training_readiness_score
        )
        response = workout.expected_response

        physiological_demand = (
            response.physiological_load_0_100
            if response is not None
            else demand
        )
        physiological_gap = max(
            0,
            physiological_demand
            - physiological_capacity,
        )

        mechanical_gap = 0

        if (
            response is not None
            and atlas_index.biomechanical_tolerance_score
            is not None
        ):
            mechanical_gap = max(
                0,
                response.biomechanical_load_0_100
                - atlas_index.biomechanical_tolerance_score,
            )

        penalty = (
            physiological_gap * 0.60
            + mechanical_gap * 0.40
        )

        return round(
            max(
                0,
                min(100, atlas_index.score - penalty),
            )
        )

    @staticmethod
    def _result(
        workout: AdaptiveWorkout,
        atlas_index: AtlasIndexResult,
        demand: int,
        compatibility: int,
        action: TrainingDecisionAction,
        reasons: list[str],
        *,
        duration_factor: float = 1.0,
        intensity_factor: float = 1.0,
        replacement_type: Optional[WorkoutType] = None,
        shift_days: int = 0,
        safety_alerts: Optional[list[str]] = None,
    ) -> TrainingDecision:
        return TrainingDecision(
            workout_id=workout.workout_id,
            action=action,
            atlas_index_score=atlas_index.score,
            session_demand_score=demand,
            compatibility_score=compatibility,
            duration_factor=duration_factor,
            intensity_factor=intensity_factor,
            replacement_type=replacement_type,
            shift_days=shift_days,
            reasons=reasons,
            safety_alerts=safety_alerts or [],
        )