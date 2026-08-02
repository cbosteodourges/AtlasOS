"""
ATLAS OS
Connecteur de démonstration pour tester l'architecture commune.
"""

from typing import Iterable

from .activity_schema import ActivitySample, NormalizedActivity
from .base import ActivityConnector


class DemoConnector(ActivityConnector):
    """Connecteur local simulant l'importation d'une activité."""

    provider = "demo"

    def __init__(self) -> None:
        self.connected = False

    def connect(self) -> None:
        """Simule la connexion au fournisseur."""
        self.connected = True

    def fetch_activities(
        self,
        since: str | None = None,
    ) -> Iterable[ActivitySample]:
        """Retourne un échantillon d'activité simulé."""
        if not self.connected:
            raise RuntimeError(
                "Le connecteur de démonstration n'est pas connecté."
            )

        return [
            ActivitySample(
                timestamp="2026-08-02T08:00:00+02:00",
                heart_rate_bpm=152.0,
                speed_mps=2.78,
                cadence_spm=168.0,
                power_watts=285.0,
                altitude_m=42.0,
                latitude=50.4360,
                longitude=2.9870,
            )
        ]

    def normalize(
        self,
        activity: ActivitySample,
    ) -> NormalizedActivity:
        """Convertit l'échantillon simulé au format commun ATLAS."""
        return NormalizedActivity(
            provider=self.provider,
            external_id="demo-run-001",
            activity_type="running",
            start_time=activity.timestamp,
            duration_seconds=3600.0,
            distance_meters=10000.0,
            calories_kcal=780.0,
            average_heart_rate_bpm=activity.heart_rate_bpm,
            maximum_heart_rate_bpm=174.0,
            average_speed_mps=activity.speed_mps,
            elevation_gain_m=85.0,
            training_load=92.0,
            source_device="ATLAS Demo Watch",
            samples=[activity],
            raw_metadata={
                "environment": "development",
                "since": None,
            },
        )