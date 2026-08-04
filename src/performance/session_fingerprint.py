"""
ATLAS OS
Empreinte individualisée des séances d'entraînement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class SessionFingerprint:
    """
    Représentation normalisée d'une séance.

    L'empreinte permet de comparer des séances différentes
    et d'apprendre progressivement leurs effets individuels.
    """

    activity_id: str
    start_time: datetime
    sport: str
    session_type: str

    distance_km: float
    duration_minutes: float
    elevation_gain_m: float

    pace_seconds_per_km: Optional[float] = None
    average_speed_kmh: Optional[float] = None
    average_heart_rate_bpm: Optional[float] = None
    maximum_heart_rate_bpm: Optional[float] = None
    aerobic_efficiency: Optional[float] = None

    training_load: Optional[float] = None
    perceived_effort_1_to_10: Optional[float] = None
    feeling_score_0_to_100: Optional[float] = None
    aerobic_training_effect: Optional[float] = None
    anaerobic_training_effect: Optional[float] = None
    body_battery_impact: Optional[float] = None
    temperature_c: Optional[float] = None

    external_load_score: int = 0
    internal_load_score: int = 0
    intensity_score: int = 0
    immediate_response_score: Optional[int] = None

    data_quality_score: int = 0
    fingerprint_confidence_score: int = 0

    classification_reasons: List[str] = field(
        default_factory=list
    )
    missing_data: List[str] = field(
        default_factory=list
    )


@dataclass
class SessionTypeEffectiveness:
    """
    Synthèse de l'efficacité observée d'un type de séance.

    Cette synthèse sera enrichie avec les réponses à 24–72 heures
    et les effets longitudinaux lorsque ces données seront présentes.
    """

    session_type: str
    session_count: int

    average_distance_km: float
    average_duration_minutes: float
    average_external_load_score: float
    average_internal_load_score: float
    average_intensity_score: float

    average_perceived_effort: Optional[float] = None
    average_feeling_score: Optional[float] = None
    average_aerobic_efficiency: Optional[float] = None
    average_immediate_response_score: Optional[float] = None

    effectiveness_score: int = 0
    confidence_score: int = 0

    positive_signals: List[str] = field(
        default_factory=list
    )
    warning_signals: List[str] = field(
        default_factory=list
    )


@dataclass
class AthleteSessionLearning:
    """Mémoire des réponses individuelles aux séances."""

    athlete_id: str
    fingerprint_count: int

    fingerprints: List[SessionFingerprint] = field(
        default_factory=list
    )
    session_type_effectiveness: List[
        SessionTypeEffectiveness
    ] = field(default_factory=list)

    global_confidence_score: int = 0
    conclusions: List[str] = field(
        default_factory=list
    )