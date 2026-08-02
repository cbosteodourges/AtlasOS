"""
ATLAS OS
Connecteur d'activités Strava.
"""

import json
from datetime import datetime
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .activity_schema import NormalizedActivity, RawActivity
from .base import ActivityConnector


class StravaConnector(ActivityConnector):
    """Importe et normalise les activités de l'API Strava V3."""

    provider = "strava"
    api_base_url = "https://www.strava.com/api/v3"

    def __init__(self, access_token: str) -> None:
        self.access_token = access_token.strip()
        self.connected = False

    def connect(self) -> None:
        """Valide la présence du jeton d'accès Strava."""
        if not self.access_token:
            raise ValueError(
                "Un jeton d'accès Strava est nécessaire."
            )

        self.connected = True

    def fetch_activities(
        self,
        since: str | None = None,
    ) -> Iterable[RawActivity]:
        """Récupère les activités de l'athlète connecté."""
        if not self.connected:
            raise RuntimeError(
                "Le connecteur Strava n'est pas connecté."
            )

        parameters: Dict[str, Any] = {
            "page": 1,
            "per_page": 100,
        }

        if since:
            parameters["after"] = self._to_epoch(since)

        url = (
            f"{self.api_base_url}/athlete/activities?"
            f"{urlencode(parameters)}"
        )

        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
        )

        with urlopen(request, timeout=30) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

        if not isinstance(payload, list):
            raise ValueError(
                "La réponse Strava ne contient pas une liste d'activités."
            )

        return [
            RawActivity(
                provider=self.provider,
                external_id=str(activity["id"]),
                payload=activity,
            )
            for activity in payload
        ]

    def normalize(
        self,
        activity: RawActivity,
    ) -> NormalizedActivity:
        """Convertit une activité Strava au format commun ATLAS."""
        payload = activity.payload

        return NormalizedActivity(
            provider=self.provider,
            external_id=activity.external_id,
            activity_type=self._activity_type(payload),
            start_time=str(payload["start_date"]),
            duration_seconds=float(
                payload.get(
                    "moving_time",
                    payload.get("elapsed_time", 0),
                )
            ),
            distance_meters=self._optional_float(
                payload.get("distance")
            ),
            calories_kcal=self._optional_float(
                payload.get("calories")
            ),
            average_heart_rate_bpm=self._optional_float(
                payload.get("average_heartrate")
            ),
            maximum_heart_rate_bpm=self._optional_float(
                payload.get("max_heartrate")
            ),
            average_speed_mps=self._optional_float(
                payload.get("average_speed")
            ),
            elevation_gain_m=self._optional_float(
                payload.get("total_elevation_gain")
            ),
            training_load=self._optional_float(
                payload.get("suffer_score")
            ),
            source_device=payload.get("device_name"),
            samples=activity.samples,
            raw_metadata={
                "name": payload.get("name"),
                "sport_type": payload.get("sport_type"),
                "elapsed_time": payload.get("elapsed_time"),
                "commute": payload.get("commute"),
                "trainer": payload.get("trainer"),
                "private": payload.get("private"),
                "received_at": activity.received_at,
            },
        )

    @staticmethod
    def _activity_type(payload: Dict[str, Any]) -> str:
        activity_type = payload.get(
            "sport_type",
            payload.get("type", "unknown"),
        )
        return str(activity_type).strip().lower()

    @staticmethod
    def _optional_float(
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        return float(value)

    @staticmethod
    def _to_epoch(value: str) -> int:
        normalized_value = value.replace("Z", "+00:00")
        return int(
            datetime.fromisoformat(
                normalized_value
            ).timestamp()
        )