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
from .registry import ConnectorRegistry
from .strava import StravaConnector
from .sync_service import ActivitySyncService

__all__ = [
    "ActivitySample",
    "RawActivity",
    "NormalizedActivity",
    "ActivityConnector",
    "DemoConnector",
    "GarminConnector",
    "GarminHistoryConnector",
    "StravaConnector",
    "ConnectorRegistry",
    "ActivitySyncService",
]