"""
ATLAS OS
Connecteur d'activités Strava.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .activity_schema import ActivitySample, NormalizedActivity, RawActivity
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

        activities = []
        page = 1
        while True:
            parameters: Dict[str, Any] = {"page": page, "per_page": 100}
            if since:
                parameters["after"] = self._to_epoch(since)
            payload = self._get_json(
                f"{self.api_base_url}/athlete/activities?{urlencode(parameters)}"
            )
            if not isinstance(payload, list):
                raise ValueError("La réponse Strava ne contient pas une liste d'activités.")
            activities.extend(
                RawActivity(provider=self.provider, external_id=str(item["id"]), payload=item)
                for item in payload
            )
            if len(payload) < 100:
                break
            page += 1
        return activities

    def _get_json(self, url: str) -> Any:
        request = Request(url, headers={
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        })
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def enrich(self, activity: RawActivity) -> RawActivity:
        """Ajoute détail, tours et flux. À utiliser pour les nouvelles séances.

        L'historique massif reste résumé pour respecter les quotas Strava ; les
        FIT conservent la priorité pour les anciennes séances détaillées.
        """
        identifier = activity.external_id
        detail = self._get_json(f"{self.api_base_url}/activities/{identifier}")
        laps = self._get_json(f"{self.api_base_url}/activities/{identifier}/laps")
        keys = "time,distance,latlng,altitude,velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth"
        streams = self._get_json(
            f"{self.api_base_url}/activities/{identifier}/streams?keys={keys}&key_by_type=true"
        )
        payload = {**activity.payload, **(detail if isinstance(detail, dict) else {})}
        payload["laps"] = laps if isinstance(laps, list) else []
        payload["streams"] = streams if isinstance(streams, dict) else {}
        return RawActivity(provider=activity.provider, external_id=identifier,
                           payload=payload, samples=self._stream_samples(
                               payload["streams"], str(payload.get("start_date") or "")
                           ))

    @staticmethod
    def _stream_samples(streams: Dict[str, Any], start_time: str = "") -> list[ActivitySample]:
        def data(name: str) -> list[Any]:
            value = streams.get(name) or {}
            return value.get("data", []) if isinstance(value, dict) else []
        times = data("time")
        if not times:
            return []
        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            start = None
        samples = []
        for index, elapsed in enumerate(times):
            latlng = data("latlng")
            coordinate = latlng[index] if index < len(latlng) else None
            def at(name: str):
                values = data(name)
                return values[index] if index < len(values) else None
            samples.append(ActivitySample(
                timestamp=(start + timedelta(seconds=int(elapsed))).isoformat()
                if start else str(int(elapsed)),
                heart_rate_bpm=at("heartrate"), speed_mps=at("velocity_smooth"),
                cadence_spm=at("cadence"), power_watts=at("watts"),
                altitude_m=at("altitude"), distance_meters=at("distance"),
                temperature_c=at("temp"),
                grade_percent=at("grade_smooth"),
                moving=at("moving"),
                latitude=coordinate[0] if coordinate else None,
                longitude=coordinate[1] if coordinate else None,
            ))
        return samples

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
                "description": payload.get("description"),
                "sport_type": payload.get("sport_type"),
                "type": payload.get("type"),
                "elapsed_time": payload.get("elapsed_time"),
                "commute": payload.get("commute"),
                "trainer": payload.get("trainer"),
                "private": payload.get("private"),
                "workout_type": payload.get("workout_type"),
                "perceived_exertion": payload.get("perceived_exertion"),
                "gear_id": payload.get("gear_id"),
                "map": payload.get("map"),
                "start_latlng": payload.get("start_latlng"),
                "end_latlng": payload.get("end_latlng"),
                "splits_metric": payload.get("splits_metric", []),
                "splits_standard": payload.get("splits_standard", []),
                "best_efforts": payload.get("best_efforts", []),
                "segment_efforts": payload.get("segment_efforts", []),
                "received_at": activity.received_at,
                "laps": payload.get("laps", []),
                "streams_available": sorted((payload.get("streams") or {}).keys()),
                "average_cadence": payload.get("average_cadence"),
                "average_power": payload.get("average_watts"),
                "maximum_power": payload.get("max_watts"),
                "weighted_average_power": payload.get("weighted_average_watts"),
                "kilojoules": payload.get("kilojoules"),
                "device_watts": payload.get("device_watts"),
                "has_heartrate": payload.get("has_heartrate"),
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
