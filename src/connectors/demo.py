"""
ATLAS OS
Connecteur de démonstration pour tester l'architecture commune.
"""

from typing import Iterable

from .activity_schema import (
    ActivitySample,
    NormalizedActivity,
    RawActivity,
)
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
    ) -> Iterable[RawActivity]:
        """Retourne une activité brute simulée."""
        if not self.connected:
            raise RuntimeError(
                "Le connecteur de démonstration n'est pas connecté."
            )

        sample = ActivitySample(
            timestamp="2026-08-02T08:00:00+02:00",
            heart_rate_bpm=152.0,
            speed_mps=2.78,
            cadence_spm=168.0,
            power_watts=285.0,
            altitude_m=42.0,
            latitude=50.4360,
            longitude=2.9870,
        )

        return [
            RawActivity(
                provider=self.provider,
                external_id="demo-run-001",
                payload={
                    "activity_type": "running",
                    "start_time": sample.timestamp,
                    "duration_seconds": 3600.0,
                    "distance_meters": 10000.0,
                    "calories_kcal": 780.0,
                    "average_heart_rate_bpm": 152.0,
                    "maximum_heart_rate_bpm": 174.0,
                    "average_speed_mps": 2.78,
                    "elevation_gain_m": 85.0,
                    "training_load": 92.0,
                    "source_device": "ATLAS Demo Watch",
                    "since": since,
                },
                samples=[sample],
            )
        ]

    def normalize(
        self,
        activity: RawActivity,
    ) -> NormalizedActivity:
        """Convertit l'activité brute au format commun ATLAS."""
        payload = activity.payload

        return NormalizedActivity(
            provider=activity.provider,
            external_id=activity.external_id,
            activity_type=payload["activity_type"],
            start_time=payload["start_time"],
            duration_seconds=payload["duration_seconds"],
            distance_meters=payload.get("distance_meters"),
            calories_kcal=payload.get("calories_kcal"),
            average_heart_rate_bpm=payload.get(
                "average_heart_rate_bpm"
            ),
            maximum_heart_rate_bpm=payload.get(
                "maximum_heart_rate_bpm"
            ),
            average_speed_mps=payload.get("average_speed_mps"),
            elevation_gain_m=payload.get("elevation_gain_m"),
            training_load=payload.get("training_load"),
            source_device=payload.get("source_device"),
            samples=activity.samples,
            raw_metadata={
                "environment": "development",
                "since": payload.get("since"),
                "received_at": activity.received_at,
            },
        )