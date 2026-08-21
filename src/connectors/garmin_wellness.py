"""
ATLAS OS
Connecteur des données quotidiennes de bien-être Garmin.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional
from zipfile import BadZipFile, ZipFile

try:
    from garmin_fit_sdk import Decoder, Stream
except ModuleNotFoundError:  # pragma: no cover - dépend de l'installation locale
    Decoder = None
    Stream = None


@dataclass
class DailyRecoverySnapshot:
    """État physiologique et récupération pour une journée."""

    day: date

    hrv_last_night_ms: Optional[float] = None
    hrv_weekly_average_ms: Optional[float] = None
    hrv_baseline_lower_ms: Optional[float] = None
    hrv_baseline_upper_ms: Optional[float] = None
    hrv_status: Optional[str] = None
    hrv_last_night_5_min_high_ms: Optional[float] = None

    resting_heart_rate_bpm: Optional[float] = None

    sleep_score: Optional[int] = None
    sleep_quality_score: Optional[int] = None
    sleep_recovery_score: Optional[int] = None
    sleep_awakenings_count: Optional[int] = None
    sleep_average_stress: Optional[float] = None
    sleep_duration_minutes: Optional[int] = None
    sleep_levels: List[Dict[str, Any]] = field(
        default_factory=list
    )

    source: str = "garmin"
    data_quality_score: int = 0

    @property
    def hrv_available(self) -> bool:
        """Indique si la VFC nocturne est disponible."""
        return self.hrv_last_night_ms is not None

    @property
    def sleep_available(self) -> bool:
        """Indique si une évaluation du sommeil existe."""
        return (
            self.sleep_score is not None
            or bool(self.sleep_levels)
        )


class GarminWellnessConnector:
    """Importe les données quotidiennes de récupération Garmin."""

    def __init__(self, wellness_directory: str) -> None:
        self.wellness_directory = Path(wellness_directory)

    def import_archive(
        self,
        archive_path: str | Path,
    ) -> DailyRecoverySnapshot:
        """Importe et fusionne une archive Garmin quotidienne."""
        path = Path(archive_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Archive Garmin Wellness introuvable : {path}"
            )

        archive_day = self._archive_day(path)
        messages: Dict[str, List[Dict[str, Any]]] = {}

        try:
            with ZipFile(path) as archive:
                fit_names = sorted(
                    name
                    for name in archive.namelist()
                    if name.lower().endswith(".fit")
                    and not name.endswith("/")
                )

                with TemporaryDirectory() as temporary_directory:
                    temporary_path = Path(temporary_directory)

                    for index, fit_name in enumerate(fit_names):
                        fit_path = (
                            temporary_path
                            / f"{index:04d}_{Path(fit_name).name}"
                        )
                        fit_path.write_bytes(
                            archive.read(fit_name)
                        )
                        self._merge_fit_messages(
                            fit_path,
                            messages,
                        )
        except BadZipFile as error:
            raise ValueError(
                f"Archive Garmin Wellness invalide : {path}"
            ) from error

        return self.build_snapshot(
            archive_day,
            messages,
        )

    def import_all(
        self,
    ) -> List[DailyRecoverySnapshot]:
        """Importe toutes les archives quotidiennes disponibles."""
        if not self.wellness_directory.is_dir():
            raise FileNotFoundError(
                "Dossier Garmin Wellness introuvable : "
                f"{self.wellness_directory}"
            )

        snapshots = [
            self.import_archive(archive_path)
            for archive_path in sorted(
                self.wellness_directory.glob("*.zip")
            )
        ]

        return sorted(
            snapshots,
            key=lambda snapshot: snapshot.day,
        )

    def import_all_cached(
        self,
        cache_path: str | Path,
    ) -> List[DailyRecoverySnapshot]:
        """Réutilise les journées déjà décodées et actualise le cache."""
        if not self.wellness_directory.is_dir():
            raise FileNotFoundError(
                "Dossier Garmin Wellness introuvable : "
                f"{self.wellness_directory}"
            )

        cache_file = Path(cache_path)
        cached_archives = self._load_cache(cache_file).get(
            "archives",
            {},
        )
        current_archives: Dict[str, Dict[str, Any]] = {}
        snapshots: List[DailyRecoverySnapshot] = []

        for archive_path in sorted(
            self.wellness_directory.glob("*.zip")
        ):
            statistics = archive_path.stat()
            signature = {
                "size": statistics.st_size,
                "mtime_ns": statistics.st_mtime_ns,
            }
            cached = cached_archives.get(archive_path.name)
            snapshot = None

            if (
                isinstance(cached, dict)
                and cached.get("signature") == signature
            ):
                try:
                    snapshot = self._snapshot_from_dict(
                        cached.get("snapshot")
                    )
                except (TypeError, ValueError):
                    snapshot = None

            if snapshot is None:
                snapshot = self.import_archive(archive_path)

            snapshots.append(snapshot)
            current_archives[archive_path.name] = {
                "signature": signature,
                "snapshot": self._snapshot_to_dict(snapshot),
            }

        self._write_cache(
            cache_file,
            {
                "version": 2,
                "archives": current_archives,
            },
        )
        return sorted(
            snapshots,
            key=lambda snapshot: snapshot.day,
        )

    @staticmethod
    def _load_cache(cache_path: Path) -> Dict[str, Any]:
        if not cache_path.is_file():
            return {}

        try:
            with cache_path.open(
                "r",
                encoding="utf-8",
            ) as input_file:
                payload = json.load(
                    input_file,
                    object_hook=(
                        GarminWellnessConnector
                        ._json_object_hook
                    ),
                )
        except (OSError, json.JSONDecodeError):
            return {}

        if (
            not isinstance(payload, dict)
            or payload.get("version") != 2
            or not isinstance(payload.get("archives"), dict)
        ):
            return {}

        return payload

    @staticmethod
    def _write_cache(
        cache_path: Path,
        payload: Dict[str, Any],
    ) -> None:
        cache_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary = cache_path.with_suffix(
            cache_path.suffix + ".tmp"
        )

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as output_file:
            json.dump(
                payload,
                output_file,
                ensure_ascii=False,
                indent=2,
                default=GarminWellnessConnector._json_default,
            )
            output_file.write("\n")

        temporary.replace(cache_path)

    @staticmethod
    def _json_default(value: Any) -> Dict[str, str]:
        if isinstance(value, datetime):
            return {
                "__atlas_datetime__": value.isoformat()
            }
        if isinstance(value, date):
            return {
                "__atlas_date__": value.isoformat()
            }
        raise TypeError(
            f"Type Wellness non sérialisable : "
            f"{type(value).__name__}"
        )

    @staticmethod
    def _json_object_hook(
        payload: Dict[str, Any],
    ) -> Any:
        if set(payload) == {"__atlas_datetime__"}:
            return datetime.fromisoformat(
                payload["__atlas_datetime__"]
            )
        if set(payload) == {"__atlas_date__"}:
            return date.fromisoformat(
                payload["__atlas_date__"]
            )
        return payload
    @staticmethod
    def _snapshot_to_dict(
        snapshot: DailyRecoverySnapshot,
    ) -> Dict[str, Any]:
        payload = asdict(snapshot)
        payload["day"] = snapshot.day.isoformat()
        return payload

    @staticmethod
    def _snapshot_from_dict(
        payload: Any,
    ) -> DailyRecoverySnapshot:
        if not isinstance(payload, dict):
            raise TypeError("Snapshot Wellness en cache invalide.")

        values = dict(payload)
        values["day"] = date.fromisoformat(
            str(values["day"])
        )
        return DailyRecoverySnapshot(**values)
    def build_snapshot(
        self,
        day: date,
        messages: Dict[str, List[Dict[str, Any]]],
    ) -> DailyRecoverySnapshot:
        """Normalise les messages FIT regroupés d’une journée."""
        hrv = self._latest(
            messages.get("hrv_status_summary_mesgs", [])
        )
        sleep = self._latest(
            messages.get("sleep_assessment_mesgs", [])
        )
        heart_rate = self._latest(
            messages.get("monitoring_hr_data_mesgs", [])
        )
        sleep_levels = list(
            messages.get("sleep_level_mesgs", [])
        )

        snapshot = DailyRecoverySnapshot(
            day=day,
            hrv_last_night_ms=self._float(
                hrv.get("last_night_average")
            ),
            hrv_weekly_average_ms=self._float(
                hrv.get("weekly_average")
            ),
            hrv_baseline_lower_ms=self._float(
                hrv.get("baseline_balanced_lower")
            ),
            hrv_baseline_upper_ms=self._float(
                hrv.get("baseline_balanced_upper")
            ),
            hrv_status=self._text(
                hrv.get("status")
            ),
            hrv_last_night_5_min_high_ms=self._float(
                hrv.get("last_night_5_min_high")
            ),
            resting_heart_rate_bpm=self._float(
                heart_rate.get(
                    "current_day_resting_heart_rate"
                )
                or heart_rate.get("resting_heart_rate")
            ),
            sleep_score=self._integer(
                sleep.get("overall_sleep_score")
            ),
            sleep_quality_score=self._integer(
                sleep.get("sleep_quality_score")
            ),
            sleep_recovery_score=self._integer(
                sleep.get("sleep_recovery_score")
            ),
            sleep_awakenings_count=self._integer(
                sleep.get("awakenings_count")
            ),
            sleep_average_stress=self._float(
                sleep.get("average_stress_during_sleep")
            ),
            sleep_duration_minutes=self._sleep_duration_minutes(
                sleep,
                sleep_levels,
            ),
            sleep_levels=sleep_levels,
        )

        snapshot.data_quality_score = (
            self._quality_score(snapshot)
        )
        return snapshot

    @classmethod
    def _sleep_duration_minutes(
        cls,
        assessment: Dict[str, Any],
        levels: List[Dict[str, Any]],
    ) -> Optional[int]:
        """Extrait la durée réellement dormie des messages FIT Garmin."""
        for key in (
            "total_sleep_time",
            "total_sleep_duration",
            "sleep_time",
            "sleep_duration",
            "total_sleep",
        ):
            minutes = cls._duration_as_minutes(assessment.get(key))
            if minutes is not None:
                return minutes

        total = 0
        found = False
        for level in levels:
            if not isinstance(level, dict):
                continue
            name = str(
                level.get("sleep_level")
                or level.get("level")
                or level.get("activity_type")
                or ""
            ).lower()
            if "awake" in name or "éveil" in name:
                continue
            for key in ("duration", "duration_seconds", "message_index_duration"):
                minutes = cls._duration_as_minutes(level.get(key))
                if minutes is not None:
                    total += minutes
                    found = True
                    break
        if found and 1 <= total <= 1200:
            return total

        # Certains exports Garmin décrivent seulement les changements
        # de phase. La durée se déduit alors des horodatages successifs.
        timed_levels = []
        for level in levels:
            if not isinstance(level, dict):
                continue
            moment = cls._as_datetime(level.get("timestamp"))
            if moment is not None:
                timed_levels.append((moment, level))
        timed_levels.sort(key=lambda item: item[0])
        assessment_end = cls._as_datetime(assessment.get("timestamp"))
        sleeping_seconds = 0.0
        for index, (start, level) in enumerate(timed_levels):
            end = (
                timed_levels[index + 1][0]
                if index + 1 < len(timed_levels)
                else assessment_end
            )
            if end is None or end <= start:
                continue
            name = str(
                level.get("sleep_level")
                or level.get("level")
                or level.get("activity_type")
                or ""
            ).lower()
            if "awake" not in name and "éveil" not in name:
                sleeping_seconds += (end - start).total_seconds()
        minutes = round(sleeping_seconds / 60)
        return minutes if 1 <= minutes <= 1200 else None

    @staticmethod
    def _as_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if value is None:
            return None
        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError:
            return None

    @staticmethod
    def _duration_as_minutes(value: Any) -> Optional[int]:
        try:
            duration = float(value)
        except (TypeError, ValueError):
            return None
        if duration <= 0:
            return None
        if duration > 172800:
            duration /= 1000
        if duration > 1440:
            duration /= 60
        minutes = round(duration)
        return minutes if 1 <= minutes <= 1200 else None

    @staticmethod
    def _archive_day(path: Path) -> date:
        try:
            return date.fromisoformat(path.stem)
        except ValueError as error:
            raise ValueError(
                "Le nom de l’archive Garmin Wellness doit suivre "
                f"le format AAAA-MM-JJ : {path.name}"
            ) from error

    @staticmethod
    def _merge_fit_messages(
        fit_path: Path,
        destination: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        if Decoder is None or Stream is None:
            raise RuntimeError(
                "Le SDK Garmin FIT n’est pas installé. "
                "Installez garmin-fit-sdk avant d’importer les données Wellness."
            )
        stream = Stream.from_file(str(fit_path))
        decoder = Decoder(stream)
        decoded_messages, _errors = decoder.read()

        for group_name, records in decoded_messages.items():
            if not isinstance(records, list):
                continue

            group = destination.setdefault(
                str(group_name),
                [],
            )

            for record in records:
                if isinstance(record, dict) and record not in group:
                    group.append(record)

    @staticmethod
    def _latest(
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not records:
            return {}

        return max(
            records,
            key=lambda record: str(
                record.get("timestamp", "")
            ),
        )

    @staticmethod
    def _float(value: Any) -> Optional[float]:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _integer(value: Any) -> Optional[int]:
        if value is None:
            return None
        return int(value)

    @staticmethod
    def _text(value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _quality_score(
        snapshot: DailyRecoverySnapshot,
    ) -> int:
        score = 0

        if snapshot.hrv_available:
            score += 35
        if snapshot.sleep_available:
            score += 35
        if snapshot.resting_heart_rate_bpm is not None:
            score += 20
        if snapshot.sleep_average_stress is not None:
            score += 10

        return min(100, score)
