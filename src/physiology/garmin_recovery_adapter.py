"""
ATLAS OS
Adaptation des données Garmin Wellness vers le moteur physiologique.
"""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Iterable, Optional

from src.connectors.garmin_wellness import (
    DailyRecoverySnapshot,
)

from .physiology_engine import PhysiologyInput


class GarminRecoveryAdapter:
    """Transforme l’historique Garmin en entrée physiologique."""

    BASELINE_WINDOW_DAYS = 28

    def build_input(
        self,
        snapshot: DailyRecoverySnapshot,
        history: Iterable[DailyRecoverySnapshot] = (),
        *,
        sleep_need_hours: float = 8.0,
        subjective_fatigue_0_10: Optional[float] = None,
        muscle_soreness_0_10: Optional[float] = None,
        pain_0_10: Optional[float] = None,
        illness_symptoms: bool = False,
        acute_load_7d: Optional[float] = None,
        chronic_load_28d: Optional[float] = None,
        vo2max: Optional[float] = None,
        vo2max_baseline: Optional[float] = None,
        notes: str = "",
    ) -> PhysiologyInput:
        """Construit les données du jour avec références personnelles."""
        previous = self._previous_snapshots(
            snapshot,
            history,
        )

        hrv_baseline = (
            snapshot.hrv_weekly_average_ms
            or self._median_available(
                item.hrv_last_night_ms
                for item in previous
            )
        )

        resting_hr_baseline = self._median_available(
            item.resting_heart_rate_bpm
            for item in previous
        )

        sleep_quality = (
            snapshot.sleep_quality_score
            if snapshot.sleep_quality_score is not None
            else snapshot.sleep_score
        )

        return PhysiologyInput(
            hrv_ms=snapshot.hrv_last_night_ms,
            hrv_baseline_ms=hrv_baseline,
            resting_hr_bpm=snapshot.resting_heart_rate_bpm,
            resting_hr_baseline_bpm=resting_hr_baseline,
            sleep_hours=self._sleep_duration_hours(
                snapshot
            ),
            sleep_need_hours=sleep_need_hours,
            sleep_quality_0_100=sleep_quality,
            stress_0_10=self._stress_0_10(
                snapshot.sleep_average_stress
            ),
            subjective_fatigue_0_10=(
                subjective_fatigue_0_10
            ),
            muscle_soreness_0_10=muscle_soreness_0_10,
            acute_load_7d=acute_load_7d,
            chronic_load_28d=chronic_load_28d,
            vo2max=vo2max,
            vo2max_baseline=vo2max_baseline,
            pain_0_10=pain_0_10,
            illness_symptoms=illness_symptoms,
            notes=notes,
        )

    def _previous_snapshots(
        self,
        snapshot: DailyRecoverySnapshot,
        history: Iterable[DailyRecoverySnapshot],
    ) -> list[DailyRecoverySnapshot]:
        minimum_ordinal = (
            snapshot.day.toordinal()
            - self.BASELINE_WINDOW_DAYS
        )

        return [
            item
            for item in history
            if minimum_ordinal <= item.day.toordinal()
            < snapshot.day.toordinal()
        ]

    @staticmethod
    def _median_available(
        values: Iterable[Optional[float]],
    ) -> Optional[float]:
        available = [
            float(value)
            for value in values
            if value is not None
        ]

        if not available:
            return None

        return float(median(available))

    @staticmethod
    def _sleep_duration_hours(
        snapshot: DailyRecoverySnapshot,
    ) -> Optional[float]:
        timestamps = [
            record.get("timestamp")
            for record in snapshot.sleep_levels
            if isinstance(record.get("timestamp"), datetime)
        ]

        if len(timestamps) < 2:
            return None

        duration_hours = (
            max(timestamps) - min(timestamps)
        ).total_seconds() / 3600.0

        if duration_hours <= 0 or duration_hours > 16:
            return None

        return round(duration_hours, 2)

    @staticmethod
    def _stress_0_10(
        garmin_stress_0_100: Optional[float],
    ) -> Optional[float]:
        if garmin_stress_0_100 is None:
            return None

        return round(
            max(
                0.0,
                min(10.0, garmin_stress_0_100 / 10.0),
            ),
            2,
        )