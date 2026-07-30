"""
ATLAS OS
Modèles de données du moteur Performance.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — ACTIVITÉ HISTORIQUE
# ████████████████████████████████████████████████████████████

@dataclass
class TrainingActivity:
    activity_date: date
    activity_type: str
    distance_km: float
    duration_minutes: int

    average_heart_rate: Optional[int] = None
    maximum_heart_rate: Optional[int] = None
    perceived_exertion: Optional[int] = None
    completed: bool = True
    notes: str = ""

    @property
    def average_speed_kmh(self) -> float:
        if self.duration_minutes <= 0:
            return 0.0

        duration_hours = self.duration_minutes / 60
        return round(self.distance_km / duration_hours, 2)

    @property
    def pace_seconds_per_km(self) -> Optional[int]:
        if self.distance_km <= 0:
            return None

        return round(
            self.duration_minutes * 60 / self.distance_km
        )


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — OBJECTIF SPORTIF
# ████████████████████████████████████████████████████████████

@dataclass
class PerformanceGoal:
    name: str
    event_date: date
    distance_km: float

    target_time_minutes: Optional[int] = None
    discipline: str = "running"
    priority: str = "principal"

    @property
    def target_pace_seconds_per_km(self) -> Optional[int]:
        if (
            self.target_time_minutes is None
            or self.distance_km <= 0
        ):
            return None

        return round(
            self.target_time_minutes * 60 / self.distance_km
        )


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟨 PARTIE C — ZONE D’ENTRAÎNEMENT
# ████████████████████████████████████████████████████████████

@dataclass
class TrainingZone:
    number: int
    name: str

    minimum_hr_percent: int
    maximum_hr_percent: int

    minimum_hr_bpm: int
    maximum_hr_bpm: int

    minimum_vma_percent: int
    maximum_vma_percent: int

    minimum_speed_kmh: float
    maximum_speed_kmh: float

    minimum_pace_seconds: Optional[int]
    maximum_pace_seconds: Optional[int]


# ████████████████████████████████████████████████████████████
# 🟨 FIN PARTIE C
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟧 PARTIE D — SÉANCE PLANIFIÉE
# ████████████████████████████████████████████████████████████

@dataclass
class PlannedWorkout:
    workout_date: date
    title: str
    description: str
    duration_minutes: int
    zone_number: int

    distance_km: Optional[float] = None
    objective: str = ""
    intensity_description: str = ""
    recovery_description: str = ""

    completed: bool = False
    perceived_exertion: Optional[int] = None
    post_session_notes: str = ""


# ████████████████████████████████████████████████████████████
# 🟧 FIN PARTIE D
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟥 PARTIE E — SEMAINE ET PLAN
# ████████████████████████████████████████████████████████████

@dataclass
class TrainingWeek:
    week_number: int
    start_date: date
    end_date: date
    objective: str
    workouts: List[PlannedWorkout] = field(default_factory=list)

    @property
    def total_duration_minutes(self) -> int:
        return sum(
            workout.duration_minutes
            for workout in self.workouts
        )

    @property
    def total_distance_km(self) -> float:
        return round(
            sum(
                workout.distance_km or 0
                for workout in self.workouts
            ),
            1,
        )


@dataclass
class TrainingPlan:
    goal: PerformanceGoal
    created_at: date
    weeks: List[TrainingWeek] = field(default_factory=list)
    explanation: str = ""

    @property
    def total_workouts(self) -> int:
        return sum(
            len(week.workouts)
            for week in self.weeks
        )


# ████████████████████████████████████████████████████████████
# 🟥 FIN PARTIE E
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟪 PARTIE F — ANALYSE HISTORIQUE
# ████████████████████████████████████████████████████████████

@dataclass
class HistoryAnalysis:
    activity_count: int
    total_distance_km: float
    average_weekly_distance_km: float
    maximum_weekly_distance_km: float
    average_sessions_per_week: float
    longest_activity_km: float
    average_rpe: Optional[float]

    strengths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    data_quality_score: int = 0


# ████████████████████████████████████████████████████████████
# 🟪 FIN PARTIE F
# ████████████████████████████████████████████████████████████