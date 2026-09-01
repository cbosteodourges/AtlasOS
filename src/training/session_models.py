"""
ATLAS OS
Modèles détaillés des séances d’entraînement adaptatives.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class WorkoutType(str, Enum):
    """Familles de séances reconnues par Atlas Coach."""

    RECOVERY_RUN = "recovery_run"
    ENDURANCE_Z2 = "endurance_z2"
    TEMPO_Z3 = "tempo_z3"
    THRESHOLD_SV2 = "threshold_sv2"
    VMA_SHORT = "vma_short"
    VMA_LONG = "vma_long"
    HILL_SPRINTS = "hill_sprints"
    MIXED_THRESHOLD_VO2 = "mixed_threshold_vo2"
    TRIANGULAR_VO2 = "triangular_vo2"
    RACE_SPECIFIC = "race_specific"
    LONG_RUN = "long_run"
    CYCLING = "cycling"
    STRENGTH = "strength"
    MOBILITY = "mobility"
    REST = "rest"


class BlockType(str, Enum):
    """Rôle d’un bloc dans une séance."""

    WARM_UP = "warm_up"
    CONTINUOUS = "continuous"
    WORK = "work"
    RECOVERY = "recovery"
    COOL_DOWN = "cool_down"
    STRENGTH = "strength"
    MOBILITY = "mobility"


class WorkoutPriority(str, Enum):
    """Importance de la séance dans la semaine."""

    KEY = "key"
    SUPPORT = "support"
    OPTIONAL = "optional"


@dataclass(slots=True)
class IntensityTarget:
    """Cibles physiologiques d’un bloc."""

    zone: Optional[int] = None
    pace_min_per_km: Optional[str] = None
    pace_max_per_km: Optional[str] = None
    heart_rate_min_bpm: Optional[int] = None
    heart_rate_max_bpm: Optional[int] = None
    speed_min_kmh: Optional[float] = None
    speed_max_kmh: Optional[float] = None
    power_min_watts: Optional[int] = None
    power_max_watts: Optional[int] = None
    rpe_0_10: Optional[float] = None
    gradient_min_percent: Optional[float] = None
    gradient_max_percent: Optional[float] = None
    intensity_pattern: str = "constant"
    transition_seconds: Optional[int] = None

    def validate(self) -> None:
        if self.zone is not None and not 1 <= self.zone <= 5:
            raise ValueError("zone doit être comprise entre 1 et 5.")
        if (
            self.rpe_0_10 is not None
            and not 0 <= self.rpe_0_10 <= 10
        ):
            raise ValueError(
                "rpe_0_10 doit être compris entre 0 et 10."
            )


@dataclass(slots=True)
class TrainingBlock:
    """Bloc élémentaire d’une séance."""

    name: str
    block_type: BlockType
    repetitions: int = 1
    duration_minutes: Optional[float] = None
    distance_meters: Optional[int] = None
    recovery_minutes: Optional[float] = None
    target: IntensityTarget = field(
        default_factory=IntensityTarget
    )
    instructions: str = ""

    def validate(self) -> None:
        if self.repetitions < 1:
            raise ValueError(
                "repetitions doit être supérieur ou égal à 1."
            )
        if (
            self.duration_minutes is None
            and self.distance_meters is None
        ):
            raise ValueError(
                "Un bloc doit définir une durée ou une distance."
            )
        if (
            self.duration_minutes is not None
            and self.duration_minutes <= 0
        ):
            raise ValueError(
                "duration_minutes doit être positive."
            )
        if (
            self.distance_meters is not None
            and self.distance_meters <= 0
        ):
            raise ValueError(
                "distance_meters doit être positive."
            )
        if (
            self.recovery_minutes is not None
            and self.recovery_minutes < 0
        ):
            raise ValueError(
                "recovery_minutes ne peut pas être négative."
            )
        self.target.validate()

    @property
    def estimated_duration_minutes(self) -> float:
        work_duration = (
            (self.duration_minutes or 0.0)
            * self.repetitions
        )
        recovery_duration = (
            (self.recovery_minutes or 0.0)
            * max(0, self.repetitions - 1)
        )
        return round(
            work_duration + recovery_duration,
            1,
        )


@dataclass(slots=True)
class ExpectedTrainingResponse:
    """Charge attendue et délai normal de récupération."""

    physiological_load_0_100: int
    biomechanical_load_0_100: int
    recovery_min_hours: int
    recovery_max_hours: int
    sensitive_structures: list[str] = field(
        default_factory=list
    )

    def validate(self) -> None:
        for name, value in (
            (
                "physiological_load_0_100",
                self.physiological_load_0_100,
            ),
            (
                "biomechanical_load_0_100",
                self.biomechanical_load_0_100,
            ),
        ):
            if not 0 <= value <= 100:
                raise ValueError(
                    f"{name} doit être compris entre 0 et 100."
                )
        if self.recovery_min_hours < 0:
            raise ValueError(
                "recovery_min_hours ne peut pas être négative."
            )
        if (
            self.recovery_max_hours
            < self.recovery_min_hours
        ):
            raise ValueError(
                "recovery_max_hours doit être supérieur "
                "ou égal à recovery_min_hours."
            )


@dataclass(slots=True)
class AdaptiveWorkout:
    """Séance détaillée pouvant être adaptée par Atlas Coach."""

    workout_id: str
    workout_date: date
    workout_type: WorkoutType
    title: str
    objective: str
    blocks: list[TrainingBlock]

    sport: str = "running"
    priority: WorkoutPriority = WorkoutPriority.SUPPORT
    planned_duration_minutes: Optional[int] = None
    planned_distance_km: Optional[float] = None
    planned_elevation_gain_m: Optional[int] = None
    planned_elevation_loss_m: Optional[int] = None
    terrain_focus: str = ""
    fueling_strategy: str = ""
    expected_response: Optional[
        ExpectedTrainingResponse
    ] = None

    movable: bool = True
    maximum_shift_days: int = 2
    replacement_types: list[WorkoutType] = field(
        default_factory=list
    )
    coach_notes: list[str] = field(
        default_factory=list
    )

    def validate(self) -> None:
        if not self.workout_id.strip():
            raise ValueError("workout_id est obligatoire.")
        if not self.title.strip():
            raise ValueError("title est obligatoire.")
        if (
            self.planned_elevation_gain_m is not None
            and self.planned_elevation_gain_m < 0
        ):
            raise ValueError(
                "planned_elevation_gain_m ne peut pas être négatif."
            )
        if (
            self.planned_elevation_loss_m is not None
            and self.planned_elevation_loss_m < 0
        ):
            raise ValueError(
                "planned_elevation_loss_m ne peut pas être négatif."
            )
        if self.maximum_shift_days < 0:
            raise ValueError(
                "maximum_shift_days ne peut pas être négatif."
            )
        if (
            not self.blocks
            and self.workout_type != WorkoutType.REST
        ):
            raise ValueError(
                "Une séance active doit contenir au moins un bloc."
            )

        for block in self.blocks:
            block.validate()

        if self.expected_response is not None:
            self.expected_response.validate()

    @property
    def estimated_duration_minutes(self) -> int:
        if self.planned_duration_minutes is not None:
            return self.planned_duration_minutes

        return round(
            sum(
                block.estimated_duration_minutes
                for block in self.blocks
            )
        )

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["workout_date"] = (
            self.workout_date.isoformat()
        )
        result["workout_type"] = self.workout_type.value
        result["priority"] = self.priority.value

        for block in result["blocks"]:
            if isinstance(block["block_type"], Enum):
                block["block_type"] = (
                    block["block_type"].value
                )

        result["replacement_types"] = [
            item.value if isinstance(item, Enum) else item
            for item in result["replacement_types"]
        ]
        return result