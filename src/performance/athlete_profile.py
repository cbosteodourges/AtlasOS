"""
ATLAS OS
Profil sportif adaptatif du moteur Performance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ThresholdHistoryEntry:
    """Valeur historique validée d'un seuil physiologique."""

    recorded_at: datetime
    speed_kmh: Optional[float] = None
    heart_rate_bpm: Optional[float] = None
    confidence_score: int = 0
    observation_count: int = 0


@dataclass
class EvolvingThreshold:
    """Seuil individuel évoluant avec les séances concordantes."""

    threshold_name: str
    speed_kmh: Optional[float] = None
    heart_rate_bpm: Optional[float] = None
    minimum_speed_kmh: Optional[float] = None
    maximum_speed_kmh: Optional[float] = None
    minimum_heart_rate_bpm: Optional[float] = None
    maximum_heart_rate_bpm: Optional[float] = None

    confidence_score: int = 0
    observation_count: int = 0
    trend: str = "unknown"
    last_updated_at: Optional[datetime] = None

    evidence: List[str] = field(
        default_factory=list
    )
    history: List[ThresholdHistoryEntry] = field(
        default_factory=list
    )


@dataclass
class PhysiologicalReferences:
    """Références physiologiques connues de l'utilisateur."""

    age_years: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None

    maximum_heart_rate_bpm: Optional[float] = None
    maximum_heart_rate_confidence_score: int = 0
    maximum_heart_rate_source: str = ""
    maximum_heart_rate_evidence: List[str] = field(
        default_factory=list
    )
    rejected_heart_rate_activity_ids: List[str] = field(
        default_factory=list
    )
    resting_heart_rate_bpm: Optional[float] = None
    threshold_heart_rate_bpm: Optional[float] = None

    vma_kmh: Optional[float] = None
    vo2_max: Optional[float] = None
    threshold_speed_kmh: Optional[float] = None

    sv1: EvolvingThreshold = field(
        default_factory=lambda: EvolvingThreshold(
            threshold_name="sv1"
        )
    )
    sv2: EvolvingThreshold = field(
        default_factory=lambda: EvolvingThreshold(
            threshold_name="sv2"
        )
    )

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

    learned_physiological_tolerance_score: float = 50.0
    learned_biomechanical_tolerance_score: float = 50.0
    learned_response_count: int = 0
    positive_response_count: int = 0
    delayed_response_count: int = 0
    adverse_response_count: int = 0

    session_type_tolerance_scores: dict[str, float] = field(
        default_factory=dict
    )
    structure_tolerance_scores: dict[str, float] = field(
        default_factory=dict
    )
    last_learning_update: Optional[datetime] = None


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
