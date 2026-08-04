"""
ATLAS OS
Profil sportif adaptatif du moteur Performance.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PhysiologicalReferences:
    """Références physiologiques connues de l'utilisateur."""

    age_years: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None

    maximum_heart_rate_bpm: Optional[float] = None
    resting_heart_rate_bpm: Optional[float] = None
    threshold_heart_rate_bpm: Optional[float] = None

    vma_kmh: Optional[float] = None
    vo2_max: Optional[float] = None
    threshold_speed_kmh: Optional[float] = None

    hrv_baseline_ms: Optional[float] = None
    body_battery_baseline: Optional[float] = None


@dataclass
class TrainingAvailability:
    """Disponibilités et contraintes d'organisation."""

    available_days_per_week: Optional[int] = None
    preferred_training_days: List[str] = field(
        default_factory=list
    )
    unavailable_days: List[str] = field(
        default_factory=list
    )
    maximum_weekly_hours: Optional[float] = None
    professional_constraints: str = ""
    family_constraints: str = ""


@dataclass
class TrainingTolerance:
    """Charge habituellement tolérée par l'utilisateur."""

    usual_running_distance_per_week_km: Optional[
        float
    ] = None
    usual_running_sessions_per_week: Optional[
        float
    ] = None
    maximum_observed_weekly_distance_km: Optional[
        float
    ] = None
    maximum_tolerated_weekly_distance_km: Optional[
        float
    ] = None

    usual_high_intensity_sessions_per_week: Optional[
        float
    ] = None
    usual_long_runs_per_month: Optional[float] = None

    usual_recovery_days_after_intensity: Optional[
        float
    ] = None
    usual_recovery_days_after_long_run: Optional[
        float
    ] = None

    recent_load_change_percent: Optional[float] = None


@dataclass
class AthleteProfile:
    """Profil individuel utilisé pour adapter ATLAS."""

    athlete_id: str
    declared_level: str
    observed_level: str

    training_age_years: Optional[float] = None
    primary_sport: str = "running"
    secondary_sports: List[str] = field(
        default_factory=list
    )

    physiological: PhysiologicalReferences = field(
        default_factory=PhysiologicalReferences
    )
    availability: TrainingAvailability = field(
        default_factory=TrainingAvailability
    )
    tolerance: TrainingTolerance = field(
        default_factory=TrainingTolerance
    )

    competition_count: int = 0
    successful_competition_count: int = 0
    preferred_competition_types: List[str] = field(
        default_factory=list
    )

    current_pain_or_injury: bool = False
    pain_or_injury_notes: str = ""
    medical_constraints: List[str] = field(
        default_factory=list
    )

    history_activity_count: int = 0
    history_duration_weeks: int = 0
    data_quality_score: int = 0
    profile_confidence_score: int = 0

    strengths: List[str] = field(
        default_factory=list
    )
    limitations: List[str] = field(
        default_factory=list
    )
    missing_data: List[str] = field(
        default_factory=list
    )