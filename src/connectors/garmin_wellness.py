"""
ATLAS OS
Connecteur des données quotidiennes de bien-être Garmin.
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional
from zipfile import BadZipFile, ZipFile

from garmin_fit_sdk import Decoder, Stream


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
            sleep_levels=sleep_levels,
        )

        snapshot.data_quality_score = (
            self._quality_score(snapshot)
        )
        return snapshot

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