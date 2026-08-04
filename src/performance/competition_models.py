"""
ATLAS OS
Modèles de l'analyse des préparations de compétition.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CompetitionEvent:
    """Compétition confirmée par l'utilisateur."""

    event_date: datetime
    title: str
    distance_km: float
    outcome: str
    outcome_label: str
    failure_at_km: Optional[float] = None
    difficulty_from_km: Optional[float] = None
    heat_level: Optional[str] = None
    elevation_context: Optional[str] = None
    notes: str = ""


@dataclass
class PreparationWindowSummary:
    """Synthèse d'une période précédant une compétition."""

    days: int
    start_at: datetime
    end_at: datetime

    activity_count: int
    running_activity_count: int
    cycling_activity_count: int
    other_activity_count: int

    running_distance_km: float
    total_duration_minutes: float
    running_duration_minutes: float
    elevation_gain_m: float

    average_running_distance_per_week_km: float
    average_running_sessions_per_week: float
    longest_running_activity_km: float

    easy_session_count: int = 0
    tempo_session_count: int = 0
    threshold_session_count: int = 0
    vo2_session_count: int = 0
    interval_session_count: int = 0
    long_run_count: int = 0
    high_intensity_session_count: int = 0

    average_heart_rate_bpm: Optional[float] = None
    average_aerobic_efficiency: Optional[float] = None
    average_training_load: Optional[float] = None
    average_aerobic_training_effect: Optional[float] = None
    average_body_battery_impact: Optional[float] = None
    average_perceived_effort: Optional[float] = None
    average_feeling_score: Optional[float] = None
    data_quality_score: int = 0


@dataclass
class TaperSummary:
    """Analyse de l'affûtage avant la compétition."""

    final_week_running_distance_km: float
    previous_three_week_average_km: float
    volume_change_percent: Optional[float]
    final_week_running_sessions: int
    days_since_last_run: Optional[int]
    days_since_last_long_run: Optional[int]
    days_since_last_intensity_session: Optional[int]


@dataclass
class PreparationPhaseSummary:
    """Synthèse d'une phase de la préparation détectée."""

    phase_name: str
    start_at: datetime
    end_at: datetime
    duration_days: int

    activity_count: int = 0
    running_activity_count: int = 0
    running_distance_km: float = 0.0
    average_running_distance_per_week_km: float = 0.0

    high_intensity_session_count: int = 0
    long_run_count: int = 0


@dataclass
class AdaptivePreparationPeriod:
    """
    Période de préparation pertinente détectée dans l'historique.

    La durée n'est pas imposée à l'avance. Elle dépend de la quantité
    d'historique disponible et des changements réellement observés
    dans l'entraînement de l'utilisateur.
    """

    event: CompetitionEvent

    detected_start_at: datetime
    detected_end_at: datetime
    duration_days: int
    duration_weeks: float

    available_history_days: int
    available_history_weeks: float
    data_limited: bool

    confidence_score: int = 0
    detection_reasons: List[str] = field(
        default_factory=list
    )
    phases: List[PreparationPhaseSummary] = field(
        default_factory=list
    )


@dataclass
class CompetitionPreparationAnalysis:
    """Analyse complète d'une préparation de compétition."""

    event: CompetitionEvent
    twelve_week_window: PreparationWindowSummary
    eight_week_window: PreparationWindowSummary
    four_week_window: PreparationWindowSummary
    final_week_window: PreparationWindowSummary
    taper: TaperSummary

    adaptive_period: Optional[
        AdaptivePreparationPeriod
    ] = None

    preparation_score: int = 0
    strengths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)


@dataclass
class CompetitionComparison:
    """Comparaison des compétitions réussies et ratées."""

    analyses: List[
        CompetitionPreparationAnalysis
    ] = field(default_factory=list)

    common_success_factors: List[str] = field(
        default_factory=list
    )
    failure_risk_factors: List[str] = field(
        default_factory=list
    )
    conclusions: List[str] = field(
        default_factory=list
    )