"""
ATLAS OS
Modèles des tendances et performances de référence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PerformanceWindowSummary:
    """Synthèse d'une période d'entraînement comparable."""

    label: str
    start_at: Optional[datetime]
    end_at: Optional[datetime]
    running_activity_count: int
    total_running_distance_km: float
    average_running_distance_per_week_km: float
    average_running_sessions_per_week: float

    average_activity_distance_km: Optional[float] = None
    average_speed_kmh: Optional[float] = None
    average_pace_seconds_per_km: Optional[float] = None
    average_heart_rate_bpm: Optional[float] = None
    average_aerobic_efficiency: Optional[float] = None
    average_cadence_spm: Optional[float] = None
    average_stride_length_m: Optional[float] = None
    average_power_watts: Optional[float] = None
    average_aerobic_training_effect: Optional[float] = None
    average_body_battery_impact: Optional[float] = None
    data_quality_score: int = 0


@dataclass
class DistancePerformanceBenchmark:
    """Meilleure activité observée sur une famille de distance."""

    label: str
    minimum_distance_km: float
    maximum_distance_km: float
    activity_count: int

    best_activity_id: Optional[str] = None
    best_activity_at: Optional[datetime] = None
    best_distance_km: Optional[float] = None
    best_duration_minutes: Optional[float] = None
    best_pace_seconds_per_km: Optional[float] = None
    best_average_heart_rate_bpm: Optional[float] = None
    best_aerobic_efficiency: Optional[float] = None
    best_average_cadence_spm: Optional[float] = None
    best_average_stride_length_m: Optional[float] = None
    best_average_power_watts: Optional[float] = None
    data_quality_score: int = 0


@dataclass
class PerformanceInsightAnalysis:
    """Comparaison des périodes et références de performance."""

    early_window: PerformanceWindowSummary
    recent_window: PerformanceWindowSummary

    average_speed_change_percent: Optional[float] = None
    pace_change_percent: Optional[float] = None
    average_heart_rate_change_percent: Optional[float] = None
    aerobic_efficiency_change_percent: Optional[float] = None
    cadence_change_percent: Optional[float] = None
    stride_length_change_percent: Optional[float] = None
    power_change_percent: Optional[float] = None

    distance_benchmarks: List[
        DistancePerformanceBenchmark
    ] = field(default_factory=list)

    strengths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)