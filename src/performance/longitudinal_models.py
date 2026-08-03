"""
ATLAS OS
Modèles du moteur d'analyse longitudinale Performance Intelligence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RunningDynamics:
    """Mesures biomécaniques et dynamiques de course."""

    average_cadence_spm: Optional[float] = None
    maximum_cadence_spm: Optional[float] = None
    average_stride_length_m: Optional[float] = None
    average_vertical_ratio_percent: Optional[float] = None
    average_vertical_oscillation_cm: Optional[float] = None
    average_ground_contact_time_ms: Optional[float] = None
    average_power_watts: Optional[float] = None
    maximum_power_watts: Optional[float] = None
    normalized_power_watts: Optional[float] = None


@dataclass
class EnvironmentMetrics:
    """Conditions environnementales de la séance."""

    average_temperature_c: Optional[float] = None
    minimum_temperature_c: Optional[float] = None
    maximum_temperature_c: Optional[float] = None
    minimum_altitude_m: Optional[float] = None
    maximum_altitude_m: Optional[float] = None


@dataclass
class RecoveryMetrics:
    """Charge interne et conséquences de la séance."""

    aerobic_training_effect: Optional[float] = None
    anaerobic_training_effect: Optional[float] = None
    body_battery_impact: Optional[float] = None
    moderate_intensity_minutes: Optional[float] = None
    vigorous_intensity_minutes: Optional[float] = None
    total_intensity_minutes: Optional[float] = None
    average_respiration_rate: Optional[float] = None
    minimum_respiration_rate: Optional[float] = None
    maximum_respiration_rate: Optional[float] = None


@dataclass
class EnergyMetrics:
    """Dépense énergétique et hydratation estimée."""

    active_calories_kcal: Optional[float] = None
    total_calories_kcal: Optional[float] = None
    estimated_sweat_loss_ml: Optional[float] = None
    carbohydrate_intake_g: Optional[float] = None
    fluid_intake_ml: Optional[float] = None


@dataclass
class LongitudinalActivity:
    """Activité complète utilisée par Performance Intelligence."""

    atlas_id: str
    start_time: datetime
    activity_type: str
    distance_km: float
    duration_minutes: float

    average_heart_rate_bpm: Optional[float] = None
    maximum_heart_rate_bpm: Optional[float] = None
    average_speed_kmh: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    training_load: Optional[float] = None

    dynamics: RunningDynamics = field(
        default_factory=RunningDynamics
    )
    environment: EnvironmentMetrics = field(
        default_factory=EnvironmentMetrics
    )
    recovery: RecoveryMetrics = field(
        default_factory=RecoveryMetrics
    )
    energy: EnergyMetrics = field(
        default_factory=EnergyMetrics
    )

    source: str = ""
    title: str = ""
    data_quality_score: int = 0

    @property
    def pace_seconds_per_km(self) -> Optional[float]:
        if self.distance_km <= 0:
            return None

        return (
            self.duration_minutes
            * 60
            / self.distance_km
        )

    @property
    def aerobic_efficiency(self) -> Optional[float]:
        if (
            not self.average_speed_kmh
            or not self.average_heart_rate_bpm
            or self.average_heart_rate_bpm <= 0
        ):
            return None

        return (
            self.average_speed_kmh
            / self.average_heart_rate_bpm
        )


@dataclass
class WeeklyPerformanceSummary:
    """Synthèse d'une semaine d'entraînement."""

    iso_year: int
    iso_week: int
    activity_count: int
    running_activity_count: int
    total_distance_km: float
    running_distance_km: float
    total_duration_minutes: float
    running_duration_minutes: float
    elevation_gain_m: float
    average_heart_rate_bpm: Optional[float] = None
    average_aerobic_efficiency: Optional[float] = None
    average_aerobic_training_effect: Optional[float] = None
    body_battery_impact: Optional[float] = None


@dataclass
class LongitudinalAnalysis:
    """Résultat interprétable de l'analyse longitudinale."""

    activity_count: int
    running_activity_count: int
    first_activity_at: Optional[datetime]
    last_activity_at: Optional[datetime]

    total_running_distance_km: float = 0.0
    average_running_distance_per_week_km: float = 0.0
    maximum_running_distance_per_week_km: float = 0.0
    average_running_sessions_per_week: float = 0.0
    longest_running_activity_km: float = 0.0

    recent_four_week_distance_km: float = 0.0
    previous_four_week_distance_km: float = 0.0
    recent_load_change_percent: Optional[float] = None

    data_quality_score: int = 0
    weekly_summaries: List[WeeklyPerformanceSummary] = field(
        default_factory=list
    )

    strengths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)