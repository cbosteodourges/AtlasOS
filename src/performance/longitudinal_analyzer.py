"""
ATLAS OS
Analyse longitudinale de l'historique Performance Intelligence v2.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Dict, List, Optional, Tuple

from .longitudinal_models import (
    LongitudinalActivity,
    LongitudinalAnalysis,
    WeeklyPerformanceSummary,
)


class LongitudinalPerformanceAnalyzer:
    """Analyse l'évolution des performances dans le temps."""

    def analyse(
        self,
        activities: List[LongitudinalActivity],
    ) -> LongitudinalAnalysis:
        if not activities:
            return LongitudinalAnalysis(
                activity_count=0,
                running_activity_count=0,
                first_activity_at=None,
                last_activity_at=None,
                warnings=[
                    "Aucune activité longitudinale disponible."
                ],
                data_quality_score=0,
            )

        ordered = sorted(
            activities,
            key=lambda activity: activity.start_time,
        )
        running_activities = [
            activity
            for activity in ordered
            if self._is_running(activity)
        ]

        weekly_summaries = self._build_weekly_summaries(
            ordered
        )
        running_weeks = [
            summary.running_distance_km
            for summary in weekly_summaries
        ]

        observed_week_count = max(
            len(weekly_summaries),
            1,
        )

        recent_distance = self._distance_in_period(
            running_activities,
            end_at=ordered[-1].start_time,
            days=28,
        )
        previous_distance = self._distance_in_period(
            running_activities,
            end_at=ordered[-1].start_time
            - timedelta(days=28),
            days=28,
        )

        analysis = LongitudinalAnalysis(
            activity_count=len(ordered),
            running_activity_count=len(
                running_activities
            ),
            first_activity_at=ordered[0].start_time,
            last_activity_at=ordered[-1].start_time,
            total_running_distance_km=round(
                sum(
                    activity.distance_km
                    for activity in running_activities
                ),
                1,
            ),
            average_running_distance_per_week_km=round(
                sum(running_weeks)
                / observed_week_count,
                1,
            ),
            maximum_running_distance_per_week_km=round(
                max(running_weeks, default=0.0),
                1,
            ),
            average_running_sessions_per_week=round(
                len(running_activities)
                / observed_week_count,
                1,
            ),
            longest_running_activity_km=round(
                max(
                    (
                        activity.distance_km
                        for activity
                        in running_activities
                    ),
                    default=0.0,
                ),
                1,
            ),
            recent_four_week_distance_km=round(
                recent_distance,
                1,
            ),
            previous_four_week_distance_km=round(
                previous_distance,
                1,
            ),
            recent_load_change_percent=(
                self._percentage_change(
                    previous_distance,
                    recent_distance,
                )
            ),
            data_quality_score=round(
                mean(
                    activity.data_quality_score
                    for activity in ordered
                )
            ),
            weekly_summaries=weekly_summaries,
        )

        self._detect_strengths(analysis)
        self._detect_warnings(analysis)
        self._build_hypotheses(
            analysis,
            running_activities,
        )

        return analysis

    def _build_weekly_summaries(
        self,
        activities: List[LongitudinalActivity],
    ) -> List[WeeklyPerformanceSummary]:
        grouped: Dict[
            Tuple[int, int],
            List[LongitudinalActivity],
        ] = defaultdict(list)

        for activity in activities:
            iso_year, iso_week, _ = (
                activity.start_time.isocalendar()
            )
            grouped[(iso_year, iso_week)].append(
                activity
            )

        first_monday = (
            activities[0].start_time
            - timedelta(
                days=activities[
                    0
                ].start_time.weekday()
            )
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        last_monday = (
            activities[-1].start_time
            - timedelta(
                days=activities[
                    -1
                ].start_time.weekday()
            )
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        summaries: List[
            WeeklyPerformanceSummary
        ] = []
        current_monday = first_monday

        while current_monday <= last_monday:
            iso_year, iso_week, _ = (
                current_monday.isocalendar()
            )
            week_activities = grouped.get(
                (iso_year, iso_week),
                [],
            )
            summaries.append(
                self._summarize_week(
                    iso_year,
                    iso_week,
                    week_activities,
                )
            )
            current_monday += timedelta(days=7)

        return summaries

    def _summarize_week(
        self,
        iso_year: int,
        iso_week: int,
        activities: List[LongitudinalActivity],
    ) -> WeeklyPerformanceSummary:
        running = [
            activity
            for activity in activities
            if self._is_running(activity)
        ]

        heart_rates = [
            activity.average_heart_rate_bpm
            for activity in running
            if activity.average_heart_rate_bpm
            is not None
        ]
        efficiencies = [
            activity.aerobic_efficiency
            for activity in running
            if activity.aerobic_efficiency
            is not None
        ]
        training_effects = [
            activity.recovery.aerobic_training_effect
            for activity in running
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

        return WeeklyPerformanceSummary(
            iso_year=iso_year,
            iso_week=iso_week,
            activity_count=len(activities),
            running_activity_count=len(running),
            total_distance_km=round(
                sum(
                    activity.distance_km
                    for activity in activities
                ),
                2,
            ),
            running_distance_km=round(
                sum(
                    activity.distance_km
                    for activity in running
                ),
                2,
            ),
            total_duration_minutes=round(
                sum(
                    activity.duration_minutes
                    for activity in activities
                ),
                1,
            ),
            running_duration_minutes=round(
                sum(
                    activity.duration_minutes
                    for activity in running
                ),
                1,
            ),
            elevation_gain_m=round(
                sum(
                    activity.elevation_gain_m or 0
                    for activity in activities
                ),
                1,
            ),
            average_heart_rate_bpm=self._average(
                heart_rates
            ),
            average_aerobic_efficiency=self._average(
                efficiencies,
                digits=4,
            ),
            average_aerobic_training_effect=self._average(
                training_effects
            ),
            body_battery_impact=(
                round(
                    sum(body_battery_values),
                    1,
                )
                if body_battery_values
                else None
            ),
        )

    def _detect_strengths(
        self,
        analysis: LongitudinalAnalysis,
    ) -> None:
        if (
            analysis.average_running_sessions_per_week
            >= 4
        ):
            analysis.strengths.append(
                "Bonne régularité de la course à pied."
            )

        if analysis.running_activity_count >= 100:
            analysis.strengths.append(
                "Historique suffisamment profond pour "
                "identifier des tendances longitudinales."
            )

        if analysis.longest_running_activity_km >= 15:
            analysis.strengths.append(
                "Capacité d'endurance longue déjà présente."
            )

        if analysis.data_quality_score >= 70:
            analysis.strengths.append(
                "Bonne richesse des données physiologiques "
                "et biomécaniques."
            )

    def _detect_warnings(
        self,
        analysis: LongitudinalAnalysis,
    ) -> None:
        weekly_distances = [
            summary.running_distance_km
            for summary in analysis.weekly_summaries
        ]

        for index in range(
            1,
            len(weekly_distances),
        ):
            previous = weekly_distances[index - 1]
            current = weekly_distances[index]

            if previous <= 0:
                continue

            increase = (
                (current - previous)
                / previous
                * 100
            )

            if increase > 20:
                analysis.warnings.append(
                    "Au moins une hausse hebdomadaire du "
                    "volume supérieure à 20 % a été détectée."
                )
                break

        if (
            analysis.recent_load_change_percent
            is not None
            and analysis.recent_load_change_percent > 20
        ):
            analysis.warnings.append(
                "Le volume des quatre dernières semaines "
                "a augmenté de plus de 20 %."
            )

        if (
            analysis.average_running_sessions_per_week
            < 3
        ):
            analysis.warnings.append(
                "La fréquence moyenne de course est "
                "inférieure à trois séances par semaine."
            )

        if analysis.data_quality_score < 60:
            analysis.warnings.append(
                "La qualité moyenne des données limite "
                "encore certaines conclusions."
            )

    def _build_hypotheses(
        self,
        analysis: LongitudinalAnalysis,
        running: List[LongitudinalActivity],
    ) -> None:
        if not running:
            analysis.hypotheses.append(
                "Aucune course à pied exploitable n'a été "
                "identifiée dans l'historique."
            )
            return

        efficiencies = [
            activity.aerobic_efficiency
            for activity in running
            if activity.aerobic_efficiency is not None
        ]

        if len(efficiencies) >= 20:
            analysis.hypotheses.append(
                "L'évolution de l'efficacité aérobie peut "
                "être comparée au volume, à la fréquence "
                "et à la récupération."
            )

        if any(
            activity.recovery.body_battery_impact
            is not None
            for activity in running
        ):
            analysis.hypotheses.append(
                "L'impact des séances sur le Body Battery "
                "pourra être associé aux performances "
                "des jours suivants."
            )

        if any(
            activity.dynamics.average_cadence_spm
            is not None
            for activity in running
        ):
            analysis.hypotheses.append(
                "Les dynamiques de course pourront être "
                "comparées entre les meilleures séances "
                "et les périodes de fatigue."
            )

        if not analysis.hypotheses:
            analysis.hypotheses.append(
                "Des données supplémentaires de récupération "
                "seront nécessaires pour expliquer les "
                "variations de performance."
            )

    @staticmethod
    def _distance_in_period(
        activities: List[LongitudinalActivity],
        end_at: datetime,
        days: int,
    ) -> float:
        start_at = end_at - timedelta(
            days=days - 1
        )

        return sum(
            activity.distance_km
            for activity in activities
            if start_at <= activity.start_time <= end_at
        )

    @staticmethod
    def _percentage_change(
        previous: float,
        current: float,
    ) -> Optional[float]:
        if previous <= 0:
            return None

        return round(
            (current - previous)
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