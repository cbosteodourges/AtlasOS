"""Formats communs des activités importées dans ATLAS OS."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ActivitySample:
    """Mesure physiologique ou géographique horodatée."""

    timestamp: str
    heart_rate_bpm: Optional[float] = None
    speed_mps: Optional[float] = None
    cadence_spm: Optional[float] = None
    power_watts: Optional[float] = None
    altitude_m: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_meters: Optional[float] = None
    temperature_c: Optional[float] = None
    vertical_oscillation_cm: Optional[float] = None
    vertical_ratio_percent: Optional[float] = None
    ground_contact_time_ms: Optional[float] = None
    stride_length_m: Optional[float] = None


@dataclass
class RawActivity:
    """Activité brute reçue depuis un fournisseur externe."""

    provider: str
    external_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    samples: List[ActivitySample] = field(default_factory=list)
    received_at: str = field(
        default_factory=lambda: datetime.now().astimezone().isoformat()
    )


@dataclass
class NormalizedActivity:
    """Activité convertie au format commun exploitable par ATLAS."""

    provider: str
    external_id: str
    activity_type: str
    start_time: str
    duration_seconds: float
    distance_meters: Optional[float] = None
    calories_kcal: Optional[float] = None
    average_heart_rate_bpm: Optional[float] = None
    maximum_heart_rate_bpm: Optional[float] = None
    average_speed_mps: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    training_load: Optional[float] = None
    source_device: Optional[str] = None
    samples: List[ActivitySample] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    source_ids: Dict[str, str] = field(default_factory=dict)
    field_provenance: Dict[str, str] = field(default_factory=dict)
    canonical_id: Optional[str] = None
    imported_at: str = field(
        default_factory=lambda: datetime.now().astimezone().isoformat()
    )

    @property
    def atlas_id(self) -> str:
        return f"{self.provider}:{self.external_id}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
