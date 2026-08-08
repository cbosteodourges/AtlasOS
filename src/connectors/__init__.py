"""Connecteurs de données pour ATLAS OS."""

from .activity_schema import (
    ActivitySample,
    NormalizedActivity,
    RawActivity,
)
from .base import ActivityConnector
from .demo import DemoConnector
from .garmin import GarminConnector
from .garmin_history import GarminHistoryConnector
from .garmin_wellness import (
    DailyRecoverySnapshot,
    GarminWellnessConnector,
)
from .manual_recovery import (
    ManualRecoveryCheckIn,
    ManualRecoveryConnector,
)
from .registry import ConnectorRegistry
from .strava import StravaConnector
from .sync_service import ActivitySyncService

__all__ = [
    "ActivityConnector",
    "ActivitySample",
    "ActivitySyncService",
    "ConnectorRegistry",
    "DailyRecoverySnapshot",
    "DemoConnector",
    "GarminConnector",
    "GarminHistoryConnector",
    "GarminWellnessConnector",
    "ManualRecoveryCheckIn",
    "ManualRecoveryConnector",
    "NormalizedActivity",
    "RawActivity",
    "StravaConnector",
]