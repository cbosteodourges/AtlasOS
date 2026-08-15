"""
ATLAS OS
Personnalisation d'un programme depuis les préparations de compétition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any


@dataclass(slots=True)
class CompetitionHistoryPersonalization:
    """Paramètres appris depuis les compétitions comparables."""

    prioritize_metabolic_quality: bool = False
    successful_analysis_count: int = 0
    failed_analysis_count: int = 0
    successful_intensity_sessions_8w: float | None = None
    failed_intensity_sessions_8w: float | None = None
    target_intensity_sessions_4w: float | None = None
    target_taper_volume_change_percent: float | None = None
    target_days_since_last_intensity: float | None = None
    confidence_score: int = 0
    explanations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class CompetitionHistoryPersonalizer:
    """Transforme les préparations comparables en préférences futures."""

    def build(
        self,
        payload: dict[str, Any],
        *,
        goal_distance_km: float,
    ) -> CompetitionHistoryPersonalization:
        analyses = [
            item
            for item in payload.get("analyses", [])
            if isinstance(item, dict)
            and self._comparable_distance(
                item,
                goal_distance_km,
            )
            and self._quality(item) >= 70
        ]
        successful = [
            item
            for item in analyses
            if str(item.get("event", {}).get("outcome", ""))
            .startswith("successful")
        ]
        failed = [
            item
            for item in analyses
            if str(item.get("event", {}).get("outcome", ""))
            == "failed"
        ]

        success_8w = self._window_values(
            successful,
            "eight_week_window",
            "high_intensity_session_count",
        )
        failed_8w = self._window_values(
            failed,
            "eight_week_window",
            "high_intensity_session_count",
        )
        success_4w = self._window_values(
            successful,
            "four_week_window",
            "high_intensity_session_count",
        )
        taper_changes = self._taper_values(
            successful,
            "volume_change_percent",
        )
        taper_delays = self._taper_values(
            successful,
            "days_since_last_intensity_session",
        )

        result = CompetitionHistoryPersonalization(
            successful_analysis_count=len(successful),
            failed_analysis_count=len(failed),
            successful_intensity_sessions_8w=(
                round(mean(success_8w), 1)
                if success_8w else None
            ),
            failed_intensity_sessions_8w=(
                round(mean(failed_8w), 1)
                if failed_8w else None
            ),
            target_intensity_sessions_4w=(
                round(mean(success_4w), 1)
                if success_4w else None
            ),
            target_taper_volume_change_percent=(
                round(mean(taper_changes), 1)
                if taper_changes else None
            ),
            target_days_since_last_intensity=(
                round(mean(taper_delays), 1)
                if taper_delays else None
            ),
        )

        success_average = result.successful_intensity_sessions_8w
        failed_average = result.failed_intensity_sessions_8w
        result.prioritize_metabolic_quality = bool(
            success_average is not None
            and success_average >= 4
            and (
                failed_average is None
                or success_average >= failed_average + 2
            )
        )
        result.confidence_score = min(
            95,
            45 + len(successful) * 20 + len(failed) * 15,
        )

        if result.prioritize_metabolic_quality:
            result.explanations.append(
                "Les préparations comparables réussies comportent "
                "nettement plus d'intensité structurée."
            )
        if not successful:
            result.warnings.append(
                "Aucune compétition comparable réussie suffisamment "
                "documentée."
            )

        return result

    @staticmethod
    def _comparable_distance(
        analysis: dict[str, Any],
        goal_distance_km: float,
    ) -> bool:
        try:
            distance = float(
                analysis.get("event", {}).get("distance_km")
            )
        except (TypeError, ValueError):
            return False
        tolerance = max(1.0, goal_distance_km * 0.15)
        return abs(distance - goal_distance_km) <= tolerance

    @staticmethod
    def _quality(analysis: dict[str, Any]) -> float:
        try:
            return float(
                analysis.get("eight_week_window", {}).get(
                    "data_quality_score",
                    0,
                )
            )
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _window_values(
        cls,
        analyses: list[dict[str, Any]],
        window: str,
        field_name: str,
    ) -> list[float]:
        return cls._numbers(
            item.get(window, {}).get(field_name)
            for item in analyses
        )

    @classmethod
    def _taper_values(
        cls,
        analyses: list[dict[str, Any]],
        field_name: str,
    ) -> list[float]:
        return cls._numbers(
            item.get("taper", {}).get(field_name)
            for item in analyses
        )

    @staticmethod
    def _numbers(values) -> list[float]:
        result = []
        for value in values:
            if value is None or isinstance(value, bool):
                continue
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                continue
        return result