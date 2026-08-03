"""
ATLAS OS
Connecteur de l'historique résumé exporté par Garmin Connect.
"""

import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .activity_schema import NormalizedActivity, RawActivity
from .base import ActivityConnector


class GarminHistoryConnector(ActivityConnector):
    """Importe l'historique CSV de Garmin Connect."""

    provider = "garmin"

    def __init__(self, csv_path: str) -> None:
        self.csv_path = Path(csv_path)
        self.connected = False

    def connect(self) -> None:
        """Vérifie que l'export CSV Garmin est disponible."""
        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"Export Garmin introuvable : {self.csv_path}"
            )

        if not self.csv_path.is_file():
            raise IsADirectoryError(
                f"Le chemin Garmin n'est pas un fichier : "
                f"{self.csv_path}"
            )

        self.connected = True

    def fetch_activities(
        self,
        since: str | None = None,
    ) -> Iterable[RawActivity]:
        """Lit toutes les activités présentes dans le CSV."""
        if not self.connected:
            raise RuntimeError(
                "Le connecteur d'historique Garmin "
                "n'est pas connecté."
            )

        activities: List[RawActivity] = []

        with self.csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.reader(csv_file)
            original_headers = next(reader, [])
            headers = self._unique_headers(
                original_headers
            )

            for values in reader:
                if not values:
                    continue

                payload = dict(
                    zip(headers, values)
                )

                start_time = self._parse_date(
                    payload.get("Date")
                )

                if not start_time:
                    continue

                if since and not self._is_after(
                    start_time,
                    since,
                ):
                    continue

                activities.append(
                    RawActivity(
                        provider=self.provider,
                        external_id=self._external_id(
                            payload
                        ),
                        payload=payload,
                    )
                )

        return activities

    def normalize(
        self,
        activity: RawActivity,
    ) -> NormalizedActivity:
        """Convertit une ligne Garmin au format commun ATLAS."""
        payload = activity.payload

        duration_seconds = self._parse_duration(
            payload.get("Durée")
        )
        distance_km = self._parse_number(
            payload.get("Distance")
        )
        distance_meters = (
            distance_km * 1000
            if distance_km is not None
            else None
        )

        average_speed_mps: Optional[float] = None

        if (
            distance_meters is not None
            and duration_seconds > 0
        ):
            average_speed_mps = (
                distance_meters / duration_seconds
            )

        return NormalizedActivity(
            provider=self.provider,
            external_id=activity.external_id,
            activity_type=self._activity_type(
                payload.get("Type d'activité")
            ),
            start_time=self._parse_date(
                payload.get("Date")
            ),
            duration_seconds=duration_seconds,
            distance_meters=distance_meters,
            calories_kcal=self._parse_number(
                payload.get("Calories")
            ),
            average_heart_rate_bpm=self._parse_number(
                payload.get(
                    "Fréquence cardiaque moyenne"
                )
            ),
            maximum_heart_rate_bpm=self._parse_number(
                payload.get(
                    "Fréquence cardiaque maximale"
                )
            ),
            average_speed_mps=average_speed_mps,
            elevation_gain_m=self._parse_number(
                payload.get("Ascension totale")
            ),
            training_load=self._parse_number(
                payload.get(
                    "Training Stress Score® (TSS®)"
                )
            ),
            source_device="Garmin Connect",
            raw_metadata={
                "title": payload.get("Titre"),
                "favorite": payload.get("Favori"),
                "average_pace": payload.get(
                    "Allure moyenne"
                ),
                "best_pace": payload.get(
                    "Meilleure allure"
                ),
                "aerobic_training_effect":
                    self._parse_number(
                        payload.get("TE aérobie")
                    ),
                "average_cadence":
                    self._parse_number(
                        payload.get(
                            "Cadence de course moyenne"
                        )
                    ),
                "maximum_cadence":
                    self._parse_number(
                        payload.get(
                            "Cadence de course maximale"
                        )
                    ),
                "average_stride_length":
                    self._parse_number(
                        payload.get(
                            "Longueur moyenne des foulées"
                        )
                    ),
                "average_gap": payload.get(
                    "GAP moyenne"
                ),
                "body_battery_consumption":
                    self._parse_number(
                        payload.get(
                            "Consommation du Body Battery"
                        )
                    ),
                "moving_time": payload.get(
                    "Temps de déplacement"
                ),
                "elapsed_time": payload.get(
                    "Temps écoulé"
                ),
                "minimum_altitude":
                    self._parse_number(
                        payload.get("Altitude minimale")
                    ),
                "maximum_altitude":
                    self._parse_number(
                        payload.get("Altitude maximale")
                    ),
                "received_at": activity.received_at,
            },
        )

    @staticmethod
    def _unique_headers(
        headers: List[str],
    ) -> List[str]:
        """Rend uniques les noms de colonnes du CSV Garmin."""
        counts: Dict[str, int] = {}
        unique_headers: List[str] = []

        for header in headers:
            count = counts.get(header, 0) + 1
            counts[header] = count

            if count == 1:
                unique_headers.append(header)
            else:
                unique_headers.append(
                    f"{header}__{count}"
                )

        return unique_headers

    @staticmethod
    def _external_id(
        payload: Dict[str, Any],
    ) -> str:
        """Crée un identifiant stable sans exposer le titre."""
        identity = "|".join(
            [
                str(payload.get("Date", "")),
                str(payload.get("Titre", "")),
                str(payload.get("Distance", "")),
                str(payload.get("Durée", "")),
            ]
        )

        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:20]

    @staticmethod
    def _activity_type(value: Any) -> str:
        normalized_value = str(
            value or "unknown"
        ).strip().lower()

        activity_types = {
            "course à pied": "running",
            "course sur tapis": "treadmill_running",
            "trail": "trail_running",
            "cyclisme": "cycling",
            "vélo en salle": "indoor_cycling",
            "vtt": "mountain_biking",
            "marche à pied": "walking",
            "marche": "walking",
            "randonnée": "hiking",
            "natation en piscine": "lap_swimming",
            "natation en eau libre": "open_water_swimming",
            "musculation": "strength_training",
            "cardio": "cardio_training",
        }

        return activity_types.get(
            normalized_value,
            normalized_value.replace(" ", "_"),
        )

    @staticmethod
    def _parse_date(value: Any) -> str:
        if not value:
            return ""

        parsed_date = datetime.strptime(
            str(value).strip(),
            "%Y-%m-%d %H:%M:%S",
        )

        return parsed_date.astimezone().isoformat()

    @staticmethod
    def _parse_duration(value: Any) -> float:
        if not value:
            return 0.0

        parts = [
            float(part)
            for part in str(value).strip().split(":")
        ]

        if len(parts) == 3:
            hours, minutes, seconds = parts
            return (
                hours * 3600
                + minutes * 60
                + seconds
            )

        if len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60 + seconds

        return parts[0]

    @staticmethod
    def _parse_number(
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        text = str(value).strip().lstrip("'")

        if not text or text == "--":
            return None

        text = text.replace(" ", "")

        if "," in text and "." in text:
            text = text.replace(",", "")
        elif re.fullmatch(
            r"-?\d{1,3}(,\d{3})+",
            text,
        ):
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")

        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _is_after(
        activity_time: str,
        since: str,
    ) -> bool:
        activity_date = datetime.fromisoformat(
            activity_time.replace("Z", "+00:00")
        )
        since_date = datetime.fromisoformat(
            since.replace("Z", "+00:00")
        )
        return activity_date > since_date