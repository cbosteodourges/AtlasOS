"""
ATLAS OS
Analyse des tendances et performances de référence.
"""

from datetime import timedelta
from statistics import mean
from typing import List, Optional

from .insight_models import (
    DistancePerformanceBenchmark,
    PerformanceInsightAnalysis,
    PerformanceWindowSummary,
)
from .longitudinal_models import LongitudinalActivity


class PerformanceInsightAnalyzer:
    """Compare les périodes et détecte les références."""

    WINDOW_DAYS = 56

    def analyse(
        self,
        activities: List[LongitudinalActivity],
    ) -> PerformanceInsightAnalysis:
        running = sorted(
            [
                activity
                for activity in activities
                if self._is_running(activity)
            ],
            key=lambda activity: activity.start_time,
        )

        if not running:
            empty_early = self._empty_window(
                "8 premières semaines"
            )
            empty_recent = self._empty_window(
                "8 dernières semaines"
            )

            return PerformanceInsightAnalysis(
                early_window=empty_early,
                recent_window=empty_recent,
                warnings=[
                    "Aucune course à pied exploitable "
                    "pour comparer les périodes."
                ],
            )

        early_start = running[0].start_time
        early_end = early_start + timedelta(
            days=self.WINDOW_DAYS - 1
        )
        recent_end = running[-1].start_time
        recent_start = recent_end - timedelta(
            days=self.WINDOW_DAYS - 1
        )

        early_activities = [
            activity
            for activity in running
            if early_start
            <= activity.start_time
            <= early_end
        ]
        recent_activities = [
            activity
            for activity in running
            if recent_start
            <= activity.start_time
            <= recent_end
        ]

        early_window = self._summarize_window(
            "8 premières semaines",
            early_start,
            early_end,
            early_activities,
        )
        recent_window = self._summarize_window(
            "8 dernières semaines",
            recent_start,
            recent_end,
            recent_activities,
        )

        analysis = PerformanceInsightAnalysis(
            early_window=early_window,
            recent_window=recent_window,
            average_speed_change_percent=(
                self._change_percent(
                    early_window.average_speed_kmh,
                    recent_window.average_speed_kmh,
                )
            ),
            pace_change_percent=(
                self._pace_improvement_percent(
                    early_window
                    .average_pace_seconds_per_km,
                    recent_window
                    .average_pace_seconds_per_km,
                )
            ),
            average_heart_rate_change_percent=(
                self._change_percent(
                    early_window
                    .average_heart_rate_bpm,
                    recent_window
                    .average_heart_rate_bpm,
                )
            ),
            aerobic_efficiency_change_percent=(
                self._change_percent(
                    early_window
                    .average_aerobic_efficiency,
                    recent_window
                    .average_aerobic_efficiency,
                )
            ),
            cadence_change_percent=(
                self._change_percent(
                    early_window.average_cadence_spm,
                    recent_window.average_cadence_spm,
                )
            ),
            stride_length_change_percent=(
                self._change_percent(
                    early_window
                    .average_stride_length_m,
                    recent_window
                    .average_stride_length_m,
                )
            ),
            power_change_percent=(
                self._change_percent(
                    early_window.average_power_watts,
                    recent_window.average_power_watts,
                )
            ),
            distance_benchmarks=[
                self._build_benchmark(
                    "Autour de 5 km",
                    4.5,
                    6.0,
                    running,
                ),
                self._build_benchmark(
                    "Autour de 10 km",
                    9.0,
                    11.5,
                    running,
                ),
                self._build_benchmark(
                    "Semi-marathon",
                    19.0,
                    23.0,
                    running,
                ),
            ],
        )

        self._detect_strengths(analysis)
        self._detect_warnings(analysis)
        self._build_hypotheses(analysis)

        return analysis

    def _summarize_window(
        self,
        label: str,
        start_at,
        end_at,
        activities: List[LongitudinalActivity],
    ) -> PerformanceWindowSummary:
        distances = [
            activity.distance_km
            for activity in activities
        ]
        speeds = [
            activity.average_speed_kmh
            for activity in activities
            if activity.average_speed_kmh is not None
        ]
        paces = [
            activity.pace_seconds_per_km
            for activity in activities
            if activity.pace_seconds_per_km is not None
        ]
        heart_rates = [
            activity.average_heart_rate_bpm
            for activity in activities
            if activity.average_heart_rate_bpm is not None
        ]
        efficiencies = [
            activity.aerobic_efficiency
            for activity in activities
            if activity.aerobic_efficiency is not None
        ]
        cadences = [
            activity.dynamics.average_cadence_spm
            for activity in activities
            if (
                activity.dynamics.average_cadence_spm
                is not None
            )
        ]
        strides = [
            activity.dynamics.average_stride_length_m
            for activity in activities
            if (
                activity.dynamics.average_stride_length_m
                is not None
            )
        ]
        powers = [
            activity.dynamics.average_power_watts
            for activity in activities
            if (
                activity.dynamics.average_power_watts
                is not None
            )
        ]
        training_effects = [
            activity.recovery.aerobic_training_effect
            for activity in activities
            if (
                activity.recovery
                .aerobic_training_effect
                is not None
            )
        ]
        body_battery_values = [
            activity.recovery.body_battery_impact
            for activity in activities
            if (
                activity.recovery.body_battery_impact
                is not None
            )
        ]
        quality_values = [
            activity.data_quality_score
            for activity in activities
        ]

        total_distance = sum(distances)

        return PerformanceWindowSummary(
            label=label,
            start_at=start_at,
            end_at=end_at,
            running_activity_count=len(activities),
            total_running_distance_km=round(
                total_distance,
                1,
            ),
            average_running_distance_per_week_km=round(
                total_distance / 8,
                1,
            ),
            average_running_sessions_per_week=round(
                len(activities) / 8,
                1,
            ),
            average_activity_distance_km=self._average(
                distances
            ),
            average_speed_kmh=self._average(
                speeds
            ),
            average_pace_seconds_per_km=self._average(
                paces
            ),
            average_heart_rate_bpm=self._average(
                heart_rates
            ),
            average_aerobic_efficiency=self._average(
                efficiencies,
                digits=4,
            ),
            average_cadence_spm=self._average(
                cadences
            ),
            average_stride_length_m=self._average(
                strides,
                digits=2,
            ),
            average_power_watts=self._average(
                powers
            ),
            average_aerobic_training_effect=self._average(
                training_effects
            ),
            average_body_battery_impact=self._average(
                body_battery_values
            ),
            data_quality_score=(
                round(mean(quality_values))
                if quality_values
                else 0
            ),
        )

    def _build_benchmark(
        self,
        label: str,
        minimum_distance_km: float,
        maximum_distance_km: float,
        activities: List[LongitudinalActivity],
    ) -> DistancePerformanceBenchmark:
        candidates = [
            activity
            for activity in activities
            if (
                minimum_distance_km
                <= activity.distance_km
                <= maximum_distance_km
                and activity.pace_seconds_per_km
                is not None
            )
        ]

        if not candidates:
            return DistancePerformanceBenchmark(
                label=label,
                minimum_distance_km=minimum_distance_km,
                maximum_distance_km=maximum_distance_km,
                activity_count=0,
            )

        best = min(
            candidates,
            key=lambda activity: (
                activity.pace_seconds_per_km
                or float("inf")
            ),
        )

        return DistancePerformanceBenchmark(
            label=label,
            minimum_distance_km=minimum_distance_km,
            maximum_distance_km=maximum_distance_km,
            activity_count=len(candidates),
            best_activity_id=best.atlas_id,
            best_activity_at=best.start_time,
            best_distance_km=round(
                best.distance_km,
                2,
            ),
            best_duration_minutes=round(
                best.duration_minutes,
                2,
            ),
            best_pace_seconds_per_km=round(
                best.pace_seconds_per_km or 0,
                1,
            ),
            best_average_heart_rate_bpm=(
                best.average_heart_rate_bpm
            ),
            best_aerobic_efficiency=(
                round(
                    best.aerobic_efficiency,
                    4,
                )
                if best.aerobic_efficiency
                is not None
                else None
            ),
            best_average_cadence_spm=(
                best.dynamics.average_cadence_spm
            ),
            best_average_stride_length_m=(
                best.dynamics.average_stride_length_m
            ),
            best_average_power_watts=(
                best.dynamics.average_power_watts
            ),
            data_quality_score=(
                best.data_quality_score
            ),
        )

    def _detect_strengths(
        self,
        analysis: PerformanceInsightAnalysis,
    ) -> None:
        if (
            analysis.aerobic_efficiency_change_percent
            is not None
            and analysis
            .aerobic_efficiency_change_percent > 3
        ):
            analysis.strengths.append(
                "L'efficacité aérobie moyenne progresse "
                "sur la période récente."
            )

        if (
            analysis.pace_change_percent is not None
            and analysis.pace_change_percent > 3
        ):
            analysis.strengths.append(
                "L'allure moyenne des séances récentes "
                "s'est améliorée."
            )

        if (
            analysis.recent_window
            .average_running_sessions_per_week >= 4
        ):
            analysis.strengths.append(
                "La période récente présente une bonne "
                "régularité d'entraînement."
            )

        available_benchmarks = sum(
            benchmark.activity_count > 0
            for benchmark
            in analysis.distance_benchmarks
        )

        if available_benchmarks >= 2:
            analysis.strengths.append(
                "L'historique contient plusieurs familles "
                "de distances comparables."
            )

    def _detect_warnings(
        self,
        analysis: PerformanceInsightAnalysis,
    ) -> None:
        early_volume = (
            analysis.early_window
            .average_running_distance_per_week_km
        )
        recent_volume = (
            analysis.recent_window
            .average_running_distance_per_week_km
        )

        volume_change = self._change_percent(
            early_volume,
            recent_volume,
        )

        if (
            volume_change is not None
            and volume_change > 25
        ):
            analysis.warnings.append(
                "Le volume hebdomadaire récent dépasse "
                "de plus de 25 % celui de la première période."
            )

        if (
            analysis.aerobic_efficiency_change_percent
            is not None
            and analysis
            .aerobic_efficiency_change_percent < -3
        ):
            analysis.warnings.append(
                "L'efficacité aérobie moyenne est en recul "
                "sur la période récente."
            )

        if (
            analysis.recent_window
            .average_running_sessions_per_week < 3
        ):
            analysis.warnings.append(
                "La période récente comporte moins de trois "
                "courses par semaine en moyenne."
            )

        if (
            analysis.recent_window.data_quality_score
            < 60
        ):
            analysis.warnings.append(
                "Les données récentes sont insuffisantes "
                "pour une comparaison forte."
            )

    def _build_hypotheses(
        self,
        analysis: PerformanceInsightAnalysis,
    ) -> None:
        if (
            analysis.pace_change_percent is not None
            and analysis
            .average_heart_rate_change_percent
            is not None
        ):
            if (
                analysis.pace_change_percent > 0
                and analysis
                .average_heart_rate_change_percent <= 0
            ):
                analysis.hypotheses.append(
                    "Une allure plus rapide avec une fréquence "
                    "cardiaque stable ou plus basse suggère "
                    "une adaptation aérobie favorable."
                )

        if (
            analysis.cadence_change_percent is not None
            or analysis.stride_length_change_percent
            is not None
        ):
            analysis.hypotheses.append(
                "Les changements de cadence et de longueur "
                "de foulée doivent être rapprochés des allures "
                "pour distinguer adaptation et fatigue."
            )

        if (
            analysis.early_window
            .average_body_battery_impact is not None
            and analysis.recent_window
            .average_body_battery_impact is not None
        ):
            analysis.hypotheses.append(
                "La consommation moyenne de Body Battery "
                "peut aider à comparer le coût de séances "
                "similaires entre les deux périodes."
            )

        if not analysis.hypotheses:
            analysis.hypotheses.append(
                "Davantage de séances comparables sont "
                "nécessaires pour expliquer les évolutions."
            )

    @staticmethod
    def _empty_window(
        label: str,
    ) -> PerformanceWindowSummary:
        return PerformanceWindowSummary(
            label=label,
            start_at=None,
            end_at=None,
            running_activity_count=0,
            total_running_distance_km=0,
            average_running_distance_per_week_km=0,
            average_running_sessions_per_week=0,
        )

    @staticmethod
    def _change_percent(
        previous: Optional[float],
        current: Optional[float],
    ) -> Optional[float]:
        if (
            previous is None
            or current is None
            or previous == 0
        ):
            return None

        return round(
            (current - previous)
            / previous
            * 100,
            1,
        )

    @staticmethod
    def _pace_improvement_percent(
        previous: Optional[float],
        current: Optional[float],
    ) -> Optional[float]:
        if (
            previous is None
            or current is None
            or previous == 0
        ):
            return None

        return round(
            (previous - current)
            / previous
            * 100,
            1,
        )

    @staticmethod
    def _average(
        values: List[float],
        digits: int = 1,
    ) -> Optional[float]:
        if not values:
            return None

        return round(
            mean(values),
            digits,
        )

    @staticmethod
    def _is_running(
        activity: LongitudinalActivity,
    ) -> bool:
        activity_type = activity.activity_type.lower()

        return (
            "running" in activity_type
            or activity_type
            in {
                "ultrafond",
                "ultra_running",
            }
        )