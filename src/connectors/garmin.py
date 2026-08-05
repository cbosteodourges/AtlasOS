"""
ATLAS OS
Connecteur Garmin fondé sur les fichiers d'activités FIT.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from garmin_fit_sdk import Decoder, Stream

from .activity_schema import (
    ActivitySample,
    NormalizedActivity,
    RawActivity,
)
from .base import ActivityConnector


class GarminConnector(ActivityConnector):
    """Importe et normalise les fichiers FIT provenant de Garmin."""

    provider = "garmin"

    def __init__(self, activities_directory: str) -> None:
        self.activities_directory = Path(activities_directory)
        self.connected = False

    def connect(self) -> None:
        """Vérifie que le dossier Garmin est disponible."""
        if not self.activities_directory.exists():
            raise FileNotFoundError(
                f"Dossier Garmin introuvable : "
                f"{self.activities_directory}"
            )

        if not self.activities_directory.is_dir():
            raise NotADirectoryError(
                f"Le chemin Garmin n'est pas un dossier : "
                f"{self.activities_directory}"
            )

        self.connected = True

    def fetch_activities(
        self,
        since: str | None = None,
    ) -> Iterable[RawActivity]:
        """Décode les fichiers FIT présents dans le dossier Garmin."""
        if not self.connected:
            raise RuntimeError(
                "Le connecteur Garmin n'est pas connecté."
            )

        activities: List[RawActivity] = []

        for fit_path in sorted(
            self.activities_directory.glob("*.fit")
        ):
            messages, errors = self._decode(fit_path)

            if errors:
                raise ValueError(
                    f"Erreur pendant le décodage de "
                    f"{fit_path.name} : {errors}"
                )

            sessions = messages.get("session_mesgs", [])

            if not sessions:
                continue

            session = sessions[0]
            start_time = self._to_iso(
                session.get("start_time")
            )

            if since and start_time:
                if not self._is_after(start_time, since):
                    continue

            cadence_multiplier = (
                2.0
                if str(
                    session.get("sport", "")
                ).strip().lower() == "running"
                else 1.0
            )

            samples = self._build_samples(
                messages.get("record_mesgs", []),
                cadence_multiplier=cadence_multiplier,
            )

            device_messages = messages.get(
                "device_info_mesgs",
                [],
            )

            activities.append(
                RawActivity(
                    provider=self.provider,
                    external_id=fit_path.stem,
                    payload={
                        "session": session,
                        "device_info": (
                            device_messages[0]
                            if device_messages
                            else {}
                        ),
                        "laps": messages.get(
                            "lap_mesgs",
                            [],
                        ),
                        "time_in_zones": messages.get(
                            "time_in_zone_mesgs",
                            [],
                        ),
                        "source_file": fit_path.name,
                    },
                    samples=samples,
                )
            )

        return activities

    def normalize(
        self,
        activity: RawActivity,
    ) -> NormalizedActivity:
        """Convertit une activité Garmin au format commun ATLAS."""
        session = activity.payload["session"]
        device_info = activity.payload.get(
            "device_info",
            {},
        )

        return NormalizedActivity(
            provider=self.provider,
            external_id=activity.external_id,
            activity_type=self._activity_type(session),
            start_time=self._to_iso(
                session.get("start_time")
            ),
            duration_seconds=float(
                session.get(
                    "total_timer_time",
                    session.get("total_elapsed_time", 0),
                )
            ),
            distance_meters=self._optional_float(
                session.get("total_distance")
            ),
            calories_kcal=self._optional_float(
                session.get("total_calories")
            ),
            average_heart_rate_bpm=self._optional_float(
                session.get("avg_heart_rate")
            ),
            maximum_heart_rate_bpm=self._optional_float(
                session.get("max_heart_rate")
            ),
            average_speed_mps=self._optional_float(
                session.get(
                    "enhanced_avg_speed",
                    session.get("avg_speed"),
                )
            ),
            elevation_gain_m=self._optional_float(
                session.get("total_ascent")
            ),
            training_load=self._training_load(session),
            source_device=self._source_device(device_info),
            samples=activity.samples,
            raw_metadata={
                "source_file": activity.payload.get(
                    "source_file"
                ),
                "sport": session.get("sport"),
                "sub_sport": session.get("sub_sport"),
                "laps": self._serializable(activity.payload.get("laps", [])),
                "time_in_zones": self._serializable(activity.payload.get("time_in_zones", [])),
                "average_cadence": self._session_cadence(session),
                "maximum_cadence": self._session_cadence(session, maximum=True),
                "average_stride_length": self._scaled_float(session.get("avg_step_length"), 1000),
                "average_vertical_ratio": self._optional_float(session.get("avg_vertical_ratio")),
                "average_vertical_oscillation": self._scaled_float(session.get("avg_vertical_oscillation"), 10),
                "average_ground_contact_time": self._optional_float(session.get("avg_stance_time")),
                "average_power": self._optional_float(session.get("avg_power")),
                "maximum_power": self._optional_float(session.get("max_power")),
                "normalized_power": self._optional_float(session.get("normalized_power")),
                "average_temperature": self._optional_float(session.get("avg_temperature")),
                "minimum_temperature": self._optional_float(session.get("min_temperature")),
                "maximum_temperature": self._optional_float(session.get("max_temperature")),
                "aerobic_training_effect": self._optional_float(session.get("total_training_effect")),
                "anaerobic_training_effect": self._optional_float(session.get("total_anaerobic_training_effect")),
                "workout_rpe_raw": self._optional_float(
                    session.get("workout_rpe")
                ),
                "perceived_effort":
                    self._perceived_effort(
                        session.get("workout_rpe")
                    ),
                "workout_feel_raw": self._optional_float(
                    session.get("workout_feel")
                ),
                "feeling_score":
                    self._optional_float(
                        session.get("workout_feel")
                    ),
                "feeling_label": self._feeling_label(
                    session.get("workout_feel")
                ),
                "total_elapsed_time": session.get(
                    "total_elapsed_time"
                ),
                "received_at": activity.received_at,
            },
        )

    @staticmethod
    def _decode(
        fit_path: Path,
    ) -> tuple[Dict[str, Any], List[Any]]:
        stream = Stream.from_file(str(fit_path))
        decoder = Decoder(stream)
        return decoder.read()

    @classmethod
    def _build_samples(
        cls,
        records: List[Dict[str, Any]],
        cadence_multiplier: float = 1.0,
    ) -> List[ActivitySample]:
        samples: List[ActivitySample] = []

        for record in records:
            timestamp = cls._to_iso(
                record.get("timestamp")
            )

            if not timestamp:
                continue

            cadence = cls._optional_float(
                record.get("cadence")
            )
            vertical_oscillation = (
                cls._optional_float(
                    record.get(
                        "vertical_oscillation"
                    )
                )
            )
            step_length = cls._optional_float(
                record.get("step_length")
            )

            samples.append(
                ActivitySample(
                    timestamp=timestamp,
                    heart_rate_bpm=cls._optional_float(
                        record.get("heart_rate")
                    ),
                    speed_mps=cls._optional_float(
                        record.get(
                            "enhanced_speed",
                            record.get("speed"),
                        )
                    ),
                    cadence_spm=(
                        cadence
                        * cadence_multiplier
                        if cadence is not None
                        else None
                    ),
                    power_watts=cls._optional_float(
                        record.get("power")
                    ),
                    altitude_m=cls._optional_float(
                        record.get(
                            "enhanced_altitude",
                            record.get("altitude"),
                        )
                    ),
                    latitude=cls._semicircles_to_degrees(
                        record.get("position_lat")
                    ),
                    longitude=cls._semicircles_to_degrees(
                        record.get("position_long")
                    ),
                    distance_meters=cls._optional_float(
                        record.get("distance")
                    ),
                    temperature_c=cls._optional_float(
                        record.get("temperature")
                    ),
                    vertical_oscillation_cm=(
                        vertical_oscillation / 10
                        if vertical_oscillation
                        is not None
                        else None
                    ),
                    vertical_ratio_percent=(
                        cls._optional_float(
                            record.get(
                                "vertical_ratio"
                            )
                        )
                    ),
                    ground_contact_time_ms=(
                        cls._optional_float(
                            record.get("stance_time")
                        )
                    ),
                    stride_length_m=(
                        step_length / 1000
                        if step_length is not None
                        else None
                    ),
                )
            )

        return samples

    @staticmethod
    def _activity_type(session: Dict[str, Any]) -> str:
        sport = str(
            session.get("sport", "unknown")
        ).strip().lower()

        sub_sport = str(
            session.get("sub_sport", "")
        ).strip().lower()

        if sub_sport and sub_sport not in {
            "generic",
            "unknown",
        }:
            return sub_sport

        return sport

    @classmethod
    def _session_cadence(
        cls,
        session: Dict[str, Any],
        maximum: bool = False,
    ) -> Optional[float]:
        """Convertit la cadence FIT en pas par minute."""
        field = (
            "max_running_cadence"
            if maximum
            else "avg_running_cadence"
        )
        fallback = (
            "max_cadence"
            if maximum
            else "avg_cadence"
        )
        cadence = cls._optional_float(
            session.get(
                field,
                session.get(fallback),
            )
        )

        if cadence is None:
            return None

        if cls._activity_type(session) == "running":
            cadence *= 2

        return cadence

    @staticmethod
    def _source_device(
        device_info: Dict[str, Any],
    ) -> Optional[str]:
        device = device_info.get(
            "garmin_product",
            device_info.get("product_name"),
        )

        if device is None:
            device = device_info.get("manufacturer")

        if device is None:
            return None

        device_name = str(device)

        known_devices = {
            "fr255": "Garmin Forerunner 255",
        }

        return known_devices.get(
            device_name.strip().lower(),
            device_name,
        )

    @staticmethod
    def _perceived_effort(
        value: Any,
    ) -> Optional[float]:
        """Convertit l'effort Garmin de 0-100 vers 0-10."""
        if value is None:
            return None

        effort = float(value)

        if effort > 10:
            effort /= 10

        return round(effort, 1)

    @staticmethod
    def _feeling_label(
        value: Any,
    ) -> Optional[str]:
        """Traduit le score Garmin de ressenti."""
        if value is None:
            return None

        feeling_labels = {
            0: "very_weak",
            25: "weak",
            50: "neutral",
            75: "strong",
            100: "very_strong",
        }

        return feeling_labels.get(
            round(float(value))
        )

    @staticmethod
    def _training_load(
        session: Dict[str, Any],
    ) -> Optional[float]:
        value = session.get(
            "training_stress_score",
            session.get("total_training_effect"),
        )

        return GarminConnector._optional_float(value)

    @classmethod
    def _serializable(
        cls,
        value: Any,
    ) -> Any:
        """Convertit r?cursivement une donn?e FIT en donn?e JSON."""
        if isinstance(value, datetime):
            return cls._to_iso(value)

        if isinstance(value, dict):
            return {
                str(key): cls._serializable(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                cls._serializable(item)
                for item in value
            ]

        return value

    @classmethod
    def _scaled_float(
        cls,
        value: Any,
        divisor: float,
    ) -> Optional[float]:
        """Convertit et redimensionne une valeur FIT optionnelle."""
        number = cls._optional_float(value)

        if number is None:
            return None

        return number / divisor

    @staticmethod
    def _optional_float(
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        return float(value)

    @staticmethod
    def _semicircles_to_degrees(
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        return float(value) * (180.0 / (2 ** 31))

    @staticmethod
    def _to_iso(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, datetime):
            return value.astimezone().isoformat()

        return str(value)

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