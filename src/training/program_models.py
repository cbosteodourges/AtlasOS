"""
ATLAS OS
Modèles des programmes d’entraînement riches et périodisés.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from src.performance.models import PerformanceGoal

from .session_models import AdaptiveWorkout


class TrainingPhase(str, Enum):
    """Phases d’une préparation sportive."""

    BASE = "base"
    DEVELOPMENT = "development"
    SPECIFIC = "specific"
    TAPER = "taper"
    RACE_WEEK = "race_week"
    RECOVERY = "recovery"


@dataclass(slots=True)
class ProgramGenerationSettings:
    """Préférences de génération du programme."""

    running_sessions_per_week: int = 4
    optional_running_sessions_per_week: int = 1
    strength_sessions_per_week: int = 2
    cycling_sessions_per_week: int = 0

    preferred_long_run_day: str = "sunday"
    preferred_quality_days: list[str] = field(
        default_factory=lambda: [
            "tuesday",
            "friday",
        ]
    )

    include_mobility: bool = True
    avoid_consecutive_intense_days: bool = True
    maximum_weekly_progression_percent: float = 8.0
    prioritize_metabolic_quality: bool = False
    race_week_sharpening_days_before: Optional[int] = None

    def validate(self) -> None:
        if not 2 <= self.running_sessions_per_week <= 7:
            raise ValueError(
                "running_sessions_per_week doit être "
                "compris entre 2 et 7."
            )
        if not 0 <= (
            self.optional_running_sessions_per_week
        ) <= 2:
            raise ValueError(
                "optional_running_sessions_per_week doit "
                "être compris entre 0 et 2."
            )
        if not 0 <= self.strength_sessions_per_week <= 4:
            raise ValueError(
                "strength_sessions_per_week doit être "
                "compris entre 0 et 4."
            )
        if not 0 <= self.cycling_sessions_per_week <= 4:
            raise ValueError(
                "cycling_sessions_per_week doit être "
                "compris entre 0 et 4."
            )
        if not 0 <= (
            self.maximum_weekly_progression_percent
        ) <= 15:
            raise ValueError(
                "maximum_weekly_progression_percent doit "
                "être compris entre 0 et 15."
            )

        if (
            self.race_week_sharpening_days_before is not None
            and not 3 <= self.race_week_sharpening_days_before <= 7
        ):
            raise ValueError(
                "race_week_sharpening_days_before doit être "
                "compris entre 3 et 7."
            )


@dataclass(slots=True)
class AdaptiveTrainingWeek:
    """Semaine détaillée d’une préparation."""

    week_number: int
    start_date: date
    end_date: date
    phase: TrainingPhase
    objective: str
    workouts: list[AdaptiveWorkout] = field(
        default_factory=list
    )
    target_running_distance_km: Optional[float] = None
    target_duration_minutes: Optional[int] = None
    is_recovery_week: bool = False
    coach_notes: list[str] = field(
        default_factory=list
    )

    @property
    def total_duration_minutes(self) -> int:
        return sum(
            workout.estimated_duration_minutes
            for workout in self.workouts
        )

    @property
    def running_workout_count(self) -> int:
        return sum(
            workout.sport == "running"
            and workout.workout_type.value != "rest"
            for workout in self.workouts
        )


@dataclass(slots=True)
class AdaptiveTrainingProgram:
    """Programme complet jusqu’à l’objectif."""

    athlete_id: str
    goal: PerformanceGoal
    created_at: date
    start_date: date
    end_date: date
    settings: ProgramGenerationSettings
    weeks: list[AdaptiveTrainingWeek] = field(
        default_factory=list
    )
    explanation: str = ""
    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def total_workouts(self) -> int:
        return sum(
            len(week.workouts)
            for week in self.weeks
        )

    @property
    def total_running_workouts(self) -> int:
        return sum(
            week.running_workout_count
            for week in self.weeks
        )

    @property
    def duration_weeks(self) -> int:
        return len(self.weeks)