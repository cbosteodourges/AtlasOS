"""Connecteurs de données pour ATLAS OS."""

from .activity_schema import (
    ActivitySample,
    NormalizedActivity,
    RawActivity,
)
from .activity_ingestion import ActivityStore, activity_fingerprint, merge_activities
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
from .health_connect_bridge import HealthConnectBridge
from .registry import ConnectorRegistry
from .source_catalog import (
    SourceCapability,
    canonical_provider,
    get_source_capability,
    list_source_capabilities,
)
from .strava import StravaConnector
from .strava_oauth import StravaOAuthService
from .sync_service import ActivitySyncService

__all__ = [
    "ActivityConnector",
    "ActivitySample",
    "ActivitySyncService",
    "ActivityStore",
    "ConnectorRegistry",
    "DailyRecoverySnapshot",
    "DemoConnector",
    "GarminConnector",
    "GarminHistoryConnector",
    "GarminWellnessConnector",
    "HealthConnectBridge",
    "ManualRecoveryCheckIn",
    "ManualRecoveryConnector",
    "NormalizedActivity",
    "RawActivity",
    "SourceCapability",
    "StravaConnector",
    "StravaOAuthService",
    "canonical_provider",
    "get_source_capability",
    "list_source_capabilities",
    "activity_fingerprint",
    "merge_activities",
]
