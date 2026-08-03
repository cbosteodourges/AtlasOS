"""
ATLAS OS
Analyse des préparations précédant les compétitions.
"""

import re
from datetime import timedelta
from statistics import mean
from typing import List, Optional

from .competition_models import (
    CompetitionComparison,
    CompetitionEvent,
    CompetitionPreparationAnalysis,
    PreparationWindowSummary,
    TaperSummary,
)
from .longitudinal_models import LongitudinalActivity


class CompetitionPreparationAnalyzer:
    """Compare les préparations des compétitions confirmées."""

    def analyse_event(
        self,
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
    ) -> CompetitionPreparationAnalysis:
        preparation = self._pre_event_activities(
            activities,
            event,
        )

        twelve_week = self._summarize_window(
            preparation,
            event,
            days=84,
        )
        eight_week = self._summarize_window(
            preparation,
            event,
            days=56,
        )
        four_week = self._summarize_window(
            preparation,
            event,
            days=28,
        )
        final_week = self._summarize_window(
            preparation,
            event,
            days=7,
        )
        taper = self._build_taper(
            preparation,
            event,
        )

        analysis = CompetitionPreparationAnalysis(
            event=event,
            twelve_week_window=twelve_week,
            eight_week_window=eight_week,
            four_week_window=four_week,
            final_week_window=final_week,
            taper=taper,
        )

        analysis.preparation_score = (
            self._preparation_score(analysis)
        )
        self._detect_strengths(analysis)
        self._detect_warnings(analysis)
        self._build_hypotheses(analysis)

        return analysis

    def compare(
        self,
        activities: List[LongitudinalActivity],
        events: List[CompetitionEvent],
    ) -> CompetitionComparison:
        analyses = [
            self.analyse_event(
                activities,
                event,
            )
            for event in events
        ]

        comparison = CompetitionComparison(
            analyses=analyses
        )

        self._compare_successes_and_failures(
            comparison
        )

        return comparison

    def _summarize_window(
        self,
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
        days: int,
    ) -> PreparationWindowSummary:
        start_at = event.event_date - timedelta(
            days=days
        )
        end_at = event.event_date

        selected = [
            activity
            for activity in activities
            if start_at
            <= activity.start_time
            < end_at
        ]
        running = [
            activity
            for activity in selected
            if self._is_running(activity)
        ]
        cycling = [
            activity
            for activity in selected
            if self._is_cycling(activity)
        ]
        other = [
            activity
            for activity in selected
            if (
                not self._is_running(activity)
                and not self._is_cycling(activity)
            )
        ]

        classifications = [
            self._classify_run(
                activity,
                event,
            )
            for activity in running
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
        training_loads = [
            activity.training_load
            for activity in selected
            if activity.training_load is not None
        ]
        training_effects = [
            activity.recovery.aerobic_training_effect
            for activity in selected
            if (
                activity.recovery
                .aerobic_training_effect
                is not None
            )
        ]
        body_battery_values = [
            activity.recovery.body_battery_impact
            for activity in selected
            if (
                activity.recovery.body_battery_impact
                is not None
            )
        ]
        perceived_efforts = [
            activity.recovery
            .perceived_effort_1_to_10
            for activity in selected
            if (
                activity.recovery
                .perceived_effort_1_to_10
                is not None
            )
        ]
        feeling_scores = [
            activity.recovery.feeling_score_0_to_100
            for activity in selected
            if (
                activity.recovery
                .feeling_score_0_to_100
                is not None
            )
        ]
        quality_scores = [
            activity.data_quality_score
            for activity in selected
        ]

        running_distance = sum(
            activity.distance_km
            for activity in running
        )
        week_count = days / 7

        intensity_labels = {
            "tempo",
            "threshold",
            "vo2",
            "interval",
        }

        return PreparationWindowSummary(
            days=days,
            start_at=start_at,
            end_at=end_at,
            activity_count=len(selected),
            running_activity_count=len(running),
            cycling_activity_count=len(cycling),
            other_activity_count=len(other),
            running_distance_km=round(
                running_distance,
                1,
            ),
            total_duration_minutes=round(
                sum(
                    activity.duration_minutes
                    for activity in selected
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
                    for activity in selected
                ),
                1,
            ),
            average_running_distance_per_week_km=round(
                running_distance / week_count,
                1,
            ),
            average_running_sessions_per_week=round(
                len(running) / week_count,
                1,
            ),
            longest_running_activity_km=round(
                max(
                    (
                        activity.distance_km
                        for activity in running
                    ),
                    default=0.0,
                ),
                1,
            ),
            easy_session_count=classifications.count(
                "easy"
            ),
            tempo_session_count=classifications.count(
                "tempo"
            ),
            threshold_session_count=(
                classifications.count("threshold")
            ),
            vo2_session_count=classifications.count(
                "vo2"
            ),
            interval_session_count=(
                classifications.count("interval")
            ),
            long_run_count=classifications.count(
                "long"
            ),
            high_intensity_session_count=sum(
                label in intensity_labels
                for label in classifications
            ),
            average_heart_rate_bpm=self._average(
                heart_rates
            ),
            average_aerobic_efficiency=self._average(
                efficiencies,
                digits=4,
            ),
            average_training_load=self._average(
                training_loads
            ),
            average_aerobic_training_effect=(
                self._average(training_effects)
            ),
            average_body_battery_impact=self._average(
                body_battery_values
            ),
            average_perceived_effort=self._average(
                perceived_efforts
            ),
            average_feeling_score=self._average(
                feeling_scores
            ),
            data_quality_score=(
                round(mean(quality_scores))
                if quality_scores
                else 0
            ),
        )

    def _build_taper(
        self,
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
    ) -> TaperSummary:
        running = [
            activity
            for activity in activities
            if self._is_running(activity)
        ]

        final_week_start = (
            event.event_date - timedelta(days=7)
        )
        previous_period_start = (
            event.event_date - timedelta(days=28)
        )

        final_week = [
            activity
            for activity in running
            if final_week_start
            <= activity.start_time
            < event.event_date
        ]
        previous_three_weeks = [
            activity
            for activity in running
            if previous_period_start
            <= activity.start_time
            < final_week_start
        ]

        final_distance = sum(
            activity.distance_km
            for activity in final_week
        )
        previous_average = (
            sum(
                activity.distance_km
                for activity in previous_three_weeks
            )
            / 3
        )

        return TaperSummary(
            final_week_running_distance_km=round(
                final_distance,
                1,
            ),
            previous_three_week_average_km=round(
                previous_average,
                1,
            ),
            volume_change_percent=(
                self._change_percent(
                    previous_average,
                    final_distance,
                )
            ),
            final_week_running_sessions=len(
                final_week
            ),
            days_since_last_run=self._days_since_last(
                running,
                event,
            ),
            days_since_last_long_run=(
                self._days_since_last(
                    [
                        activity
                        for activity in running
                        if (
                            self._classify_run(
                                activity,
                                event,
                            )
                            == "long"
                        )
                    ],
                    event,
                )
            ),
            days_since_last_intensity_session=(
                self._days_since_last(
                    [
                        activity
                        for activity in running
                        if self._classify_run(
                            activity,
                            event,
                        )
                        in {
                            "tempo",
                            "threshold",
                            "vo2",
                            "interval",
                        }
                    ],
                    event,
                )
            ),
        )

    def _preparation_score(
        self,
        analysis: CompetitionPreparationAnalysis,
    ) -> int:
        score = 30
        eight_week = analysis.eight_week_window
        four_week = analysis.four_week_window
        taper = analysis.taper

        if (
            eight_week
            .average_running_sessions_per_week >= 3
        ):
            score += 15

        if (
            eight_week
            .average_running_sessions_per_week >= 4
        ):
            score += 5

        if eight_week.long_run_count >= 2:
            score += 15

        if (
            2
            <= four_week.high_intensity_session_count
            <= 8
        ):
            score += 15

        if (
            taper.volume_change_percent is not None
            and -60
            <= taper.volume_change_percent
            <= -10
        ):
            score += 15

        if (
            taper.days_since_last_run is not None
            and 1 <= taper.days_since_last_run <= 3
        ):
            score += 5

        return min(score, 100)

    def _detect_strengths(
        self,
        analysis: CompetitionPreparationAnalysis,
    ) -> None:
        eight_week = analysis.eight_week_window
        four_week = analysis.four_week_window
        taper = analysis.taper

        if (
            eight_week
            .average_running_sessions_per_week >= 3
        ):
            analysis.strengths.append(
                "Régularité satisfaisante sur les "
                "huit semaines spécifiques."
            )

        if eight_week.long_run_count >= 2:
            analysis.strengths.append(
                "Plusieurs sorties longues ont préparé "
                "l'endurance spécifique."
            )

        if (
            2
            <= four_week.high_intensity_session_count
            <= 8
        ):
            analysis.strengths.append(
                "Le dernier mois contient un travail "
                "d'intensité structuré."
            )

        if (
            taper.volume_change_percent is not None
            and -60
            <= taper.volume_change_percent
            <= -10
        ):
            analysis.strengths.append(
                "La dernière semaine présente une réduction "
                "de volume compatible avec un affûtage."
            )

    def _detect_warnings(
        self,
        analysis: CompetitionPreparationAnalysis,
    ) -> None:
        eight_week = analysis.eight_week_window
        four_week = analysis.four_week_window
        taper = analysis.taper

        if (
            eight_week
            .average_running_sessions_per_week < 3
        ):
            analysis.warnings.append(
                "Moins de trois courses par semaine "
                "sur les huit semaines spécifiques."
            )

        if eight_week.long_run_count < 2:
            analysis.warnings.append(
                "Peu de sorties longues identifiées "
                "pendant la préparation spécifique."
            )

        if four_week.high_intensity_session_count == 0:
            analysis.warnings.append(
                "Aucune séance d'intensité identifiée "
                "pendant les quatre dernières semaines."
            )

        if four_week.high_intensity_session_count > 8:
            analysis.warnings.append(
                "Densité élevée de séances intenses "
                "pendant les quatre dernières semaines."
            )

        if (
            taper.volume_change_percent is not None
            and taper.volume_change_percent > 5
        ):
            analysis.warnings.append(
                "Le volume augmente pendant la dernière "
                "semaine au lieu de diminuer."
            )

        if taper.days_since_last_run == 0:
            analysis.warnings.append(
                "Une séance de course a été réalisée "
                "la veille de la compétition."
            )

    def _build_hypotheses(
        self,
        analysis: CompetitionPreparationAnalysis,
    ) -> None:
        event = analysis.event

        if event.heat_level == "high":
            analysis.hypotheses.append(
                "La forte chaleur constitue un facteur "
                "explicatif majeur indépendant de la qualité "
                "de la préparation."
            )

        if (
            event.outcome == "failed"
            and analysis.preparation_score >= 70
        ):
            analysis.hypotheses.append(
                "La préparation paraît cohérente malgré "
                "l'échec : les conditions du jour, l'allure "
                "initiale, l'hydratation et la thermorégulation "
                "doivent être examinées en priorité."
            )

        if event.failure_at_km is not None:
            analysis.hypotheses.append(
                "La défaillance au kilomètre "
                f"{event.failure_at_km:g} doit être rapprochée "
                "de l'allure, de la FC et de la température "
                "dans les échantillons détaillés."
            )

        if (
            analysis.taper.days_since_last_intensity_session
            is not None
        ):
            analysis.hypotheses.append(
                "Le délai entre la dernière séance intense "
                "et la compétition doit être comparé aux "
                "courses réussies."
            )

    def _compare_successes_and_failures(
        self,
        comparison: CompetitionComparison,
    ) -> None:
        successful = [
            analysis
            for analysis in comparison.analyses
            if analysis.event.outcome.startswith(
                "successful"
            )
        ]
        failed = [
            analysis
            for analysis in comparison.analyses
            if analysis.event.outcome == "failed"
        ]

        if successful:
            success_frequency = mean(
                analysis.eight_week_window
                .average_running_sessions_per_week
                for analysis in successful
            )
            success_intensity = mean(
                analysis.four_week_window
                .high_intensity_session_count
                for analysis in successful
            )

            if success_frequency >= 3:
                comparison.common_success_factors.append(
                    "Les compétitions réussies sont précédées "
                    "d'au moins trois courses hebdomadaires "
                    "en moyenne."
                )

            if success_intensity >= 2:
                comparison.common_success_factors.append(
                    "Les préparations réussies conservent "
                    "plusieurs séances d'intensité dans "
                    "le dernier mois."
                )

        if failed:
            if any(
                analysis.event.heat_level == "high"
                for analysis in failed
            ):
                comparison.failure_risk_factors.append(
                    "Une forte chaleur est présente lors "
                    "de la compétition ratée."
                )

        if successful and failed:
            success_score = mean(
                analysis.preparation_score
                for analysis in successful
            )
            failed_score = mean(
                analysis.preparation_score
                for analysis in failed
            )

            if failed_score >= success_score - 10:
                comparison.conclusions.append(
                    "La compétition ratée ne semble pas "
                    "s'expliquer uniquement par une moins "
                    "bonne préparation."
                )

            success_volume = mean(
                analysis.eight_week_window
                .average_running_distance_per_week_km
                for analysis in successful
            )
            failed_volume = mean(
                analysis.eight_week_window
                .average_running_distance_per_week_km
                for analysis in failed
            )

            comparison.conclusions.append(
                "Volume moyen sur huit semaines : "
                f"{success_volume:.1f} km/semaine avant "
                "les réussites contre "
                f"{failed_volume:.1f} km/semaine avant "
                "la compétition ratée."
            )

    def _classify_run(
        self,
        activity: LongitudinalActivity,
        event: CompetitionEvent,
    ) -> str:
        title = activity.title.lower()

        if (
            "longue course" in title
            or "sortie longue" in title
            or "long run" in title
        ):
            return "long"

        long_distance_threshold = max(
            12.0,
            event.distance_km * 0.65,
        )

        if activity.distance_km >= long_distance_threshold:
            return "long"

        if "seuil" in title:
            return "threshold"

        if (
            "vo2" in title
            or "vma" in title
        ):
            return "vo2"

        if "tempo" in title:
            return "tempo"

        if (
            "fraction" in title
            or "interval" in title
            or re.search(
                r"\d+\s*x\s*\d+",
                title,
            )
        ):
            return "interval"

        return "easy"

    @staticmethod
    def _pre_event_activities(
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
    ) -> List[LongitudinalActivity]:
        return [
            activity
            for activity in activities
            if activity.start_time < event.event_date
        ]

    @staticmethod
    def _days_since_last(
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
    ) -> Optional[int]:
        previous = [
            activity
            for activity in activities
            if activity.start_time < event.event_date
        ]

        if not previous:
            return None

        last_activity = max(
            previous,
            key=lambda activity: activity.start_time,
        )

        return (
            event.event_date.date()
            - last_activity.start_time.date()
        ).days

    @staticmethod
    def _change_percent(
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

    @staticmethod
    def _is_cycling(
        activity: LongitudinalActivity,
    ) -> bool:
        activity_type = activity.activity_type.lower()

        return (
            "cycling" in activity_type
            or "cyclisme" in activity_type
            or "biking" in activity_type
            or activity_type == "vtt"
        )