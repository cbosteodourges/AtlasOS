"""
ATLAS OS
Construction du profil sportif à partir de l'historique.
"""

from collections import defaultdict
from statistics import mean
from typing import Dict, List, Optional, Tuple

from .athlete_profile import (
    AthleteProfile,
    PhysiologicalReferences,
    TrainingAvailability,
    TrainingTolerance,
)
from .competition_models import CompetitionEvent
from .longitudinal_models import LongitudinalActivity


class AthleteProfileBuilder:
    """Construit un profil adaptatif et explicable."""

    def build(
        self,
        athlete_id: str,
        declared_level: str,
        activities: List[LongitudinalActivity],
        competitions: Optional[
            List[CompetitionEvent]
        ] = None,
        physiological: Optional[
            PhysiologicalReferences
        ] = None,
        availability: Optional[
            TrainingAvailability
        ] = None,
        training_age_years: Optional[float] = None,
    ) -> AthleteProfile:
        competitions = competitions or []
        physiological = (
            physiological
            or PhysiologicalReferences()
        )
        availability = (
            availability
            or TrainingAvailability()
        )

        ordered = sorted(
            activities,
            key=lambda activity: activity.start_time,
        )
        running = [
            activity
            for activity in ordered
            if self._is_running(activity)
        ]

        weekly_running = self._weekly_running(
            ordered,
            running,
        )
        all_weekly_values = list(
            weekly_running.values()
        )
        all_weekly_distances = [
            values["distance"]
            for values in all_weekly_values
        ]

        history_weeks = len(weekly_running)
        recent_week_count = min(
            12,
            history_weeks,
        )
        recent_weekly_values = (
            all_weekly_values[-recent_week_count:]
            if recent_week_count
            else []
        )
        weekly_distances = [
            values["distance"]
            for values in recent_weekly_values
        ]
        weekly_sessions = [
            values["sessions"]
            for values in recent_weekly_values
        ]

        recent_week_keys = set(
            list(weekly_running.keys())[
                -recent_week_count:
            ]
            if recent_week_count
            else []
        )
        recent_running = [
            activity
            for activity in running
            if (
                activity.start_time.isocalendar()[:2]
                in recent_week_keys
            )
        ]

        average_distance = self._average(
            weekly_distances
        )
        average_sessions = self._average(
            weekly_sessions
        )
        maximum_distance = max(
            all_weekly_distances,
            default=0.0,
        )

        intensity_count = sum(
            self._is_structured_intensity(
                activity
            )
            for activity in recent_running
        )

        observed_level = self._observed_level(
            declared_level=declared_level,
            history_weeks=history_weeks,
            average_distance=average_distance,
            average_sessions=average_sessions,
            competition_count=len(competitions),
            intensity_count=intensity_count,
        )

        successful_count = sum(
            event.outcome.startswith(
                "successful"
            )
            for event in competitions
        )

        tolerance = TrainingTolerance(
            usual_running_distance_per_week_km=(
                round(average_distance, 1)
            ),
            usual_running_sessions_per_week=(
                round(average_sessions, 1)
            ),
            maximum_observed_weekly_distance_km=(
                round(maximum_distance, 1)
            ),
            maximum_tolerated_weekly_distance_km=(
                self._tolerated_distance(
                    weekly_distances
                )
            ),
            usual_high_intensity_sessions_per_week=(
                round(
                    intensity_count
                    / max(history_weeks, 1),
                    1,
                )
            ),
            usual_long_runs_per_month=(
                self._long_runs_per_month(
                    recent_running,
                    recent_week_count,
                )
            ),
            recent_load_change_percent=(
                self._recent_load_change(
                    weekly_distances
                )
            ),
        )

        quality_score = (
            round(
                mean(
                    activity.data_quality_score
                    for activity in ordered
                )
            )
            if ordered
            else 0
        )

        profile = AthleteProfile(
            athlete_id=athlete_id,
            declared_level=declared_level,
            observed_level=observed_level,
            training_age_years=training_age_years,
            primary_sport="running",
            secondary_sports=self._secondary_sports(
                ordered
            ),
            physiological=physiological,
            availability=availability,
            tolerance=tolerance,
            competition_count=len(competitions),
            successful_competition_count=(
                successful_count
            ),
            preferred_competition_types=(
                self._competition_types(
                    competitions
                )
            ),
            history_activity_count=len(ordered),
            history_duration_weeks=history_weeks,
            data_quality_score=quality_score,
        )

        self._describe_profile(
            profile,
            running,
            competitions,
        )
        profile.profile_confidence_score = (
            self._confidence_score(profile)
        )

        return profile

    def _weekly_running(
        self,
        all_activities: List[LongitudinalActivity],
        running: List[LongitudinalActivity],
    ) -> Dict[Tuple[int, int], Dict[str, float]]:
        if not all_activities:
            return {}

        first = all_activities[0].start_time
        last = all_activities[-1].start_time
        first_monday = (
            first
            - self._days(first.weekday())
        )
        last_monday = (
            last
            - self._days(last.weekday())
        )

        grouped: Dict[
            Tuple[int, int],
            Dict[str, float],
        ] = defaultdict(
            lambda: {
                "distance": 0.0,
                "sessions": 0.0,
            }
        )

        current = first_monday

        while current <= last_monday:
            iso_year, iso_week, _ = (
                current.isocalendar()
            )
            grouped[(iso_year, iso_week)]
            current += self._days(7)

        for activity in running:
            iso_year, iso_week, _ = (
                activity.start_time.isocalendar()
            )
            key = (iso_year, iso_week)
            grouped[key]["distance"] += (
                activity.distance_km
            )
            grouped[key]["sessions"] += 1

        return dict(sorted(grouped.items()))

    @staticmethod
    def _days(value: int):
        from datetime import timedelta

        return timedelta(days=value)

    def _observed_level(
        self,
        declared_level: str,
        history_weeks: int,
        average_distance: float,
        average_sessions: float,
        competition_count: int,
        intensity_count: int,
    ) -> str:
        score = 0

        if history_weeks >= 12:
            score += 1

        if history_weeks >= 24:
            score += 1

        if average_sessions >= 3:
            score += 1

        if average_sessions >= 4:
            score += 1

        if average_distance >= 25:
            score += 1

        if average_distance >= 50:
            score += 1

        if competition_count >= 1:
            score += 1

        if competition_count >= 3:
            score += 1

        if intensity_count >= 8:
            score += 1

        if score <= 1:
            return "beginner"

        if score <= 3:
            return "recreational"

        if score <= 5:
            return "regular_amateur"

        if score <= 7:
            return "competitive"

        declared = declared_level.strip().lower()

        if declared in {
            "elite",
            "high_performance",
        }:
            return "high_performance"

        return "advanced"

    def _describe_profile(
        self,
        profile: AthleteProfile,
        running: List[LongitudinalActivity],
        competitions: List[CompetitionEvent],
    ) -> None:
        tolerance = profile.tolerance

        if (
            tolerance
            .usual_running_sessions_per_week
            is not None
            and tolerance
            .usual_running_sessions_per_week >= 3
        ):
            profile.strengths.append(
                "Historique de course régulier."
            )

        if competitions:
            profile.strengths.append(
                "Expérience de compétition disponible "
                "pour personnaliser les préparations."
            )

        if any(
            activity.distance_km >= 18
            for activity in running
        ):
            profile.strengths.append(
                "Expérience de l'endurance longue."
            )

        if not running:
            profile.limitations.append(
                "Aucune course exploitable."
            )

        if (
            profile.physiological
            .maximum_heart_rate_bpm
            is None
        ):
            profile.missing_data.append(
                "Fréquence cardiaque maximale"
            )

        if (
            profile.physiological
            .resting_heart_rate_bpm
            is None
        ):
            profile.missing_data.append(
                "Fréquence cardiaque au repos"
            )

        if (
            profile.physiological
            .hrv_baseline_ms
            is None
        ):
            profile.missing_data.append(
                "HRV de référence"
            )

        if (
            profile.physiological
            .vma_kmh
            is None
        ):
            profile.missing_data.append(
                "VMA"
            )

        if (
            profile.physiological
            .vo2_max
            is None
        ):
            profile.missing_data.append(
                "VO2 max"
            )

        if (
            profile.physiological
            .threshold_heart_rate_bpm
            is None
        ):
            profile.missing_data.append(
                "Fréquence cardiaque au seuil"
            )

        if (
            profile.availability
            .available_days_per_week
            is None
        ):
            profile.missing_data.append(
                "Disponibilités hebdomadaires"
            )

    @staticmethod
    def _confidence_score(
        profile: AthleteProfile,
    ) -> int:
        """
        Évalue la fiabilité réelle du profil.

        Le score repose sur la profondeur de l'historique,
        sa densité, sa qualité, l'expérience de compétition,
        les références physiologiques et les disponibilités.
        """
        score = 10

        if profile.history_duration_weeks >= 12:
            score += 10

        if profile.history_duration_weeks >= 24:
            score += 10

        if profile.history_activity_count >= 25:
            score += 10

        if profile.history_activity_count >= 100:
            score += 10

        if profile.competition_count >= 1:
            score += 8

        if profile.competition_count >= 3:
            score += 7

        if profile.data_quality_score >= 70:
            score += 15

        if (
            profile.physiological.vma_kmh
            is not None
            and profile.physiological.vo2_max
            is not None
        ):
            score += 10

        if (
            profile.physiological
            .threshold_heart_rate_bpm
            is not None
            and profile.physiological
            .threshold_speed_kmh
            is not None
        ):
            score += 10

        if (
            profile.physiological
            .resting_heart_rate_bpm
            is not None
            and profile.physiological
            .hrv_baseline_ms
            is not None
        ):
            score += 10

        if (
            profile.availability
            .available_days_per_week
            is not None
        ):
            score += 5

        confidence_limit = 100

        if (
            profile.physiological
            .resting_heart_rate_bpm
            is None
            or profile.physiological
            .hrv_baseline_ms
            is None
        ):
            confidence_limit = 90

        return min(score, confidence_limit)

    @staticmethod
    def _tolerated_distance(
        weekly_distances: List[float],
    ) -> Optional[float]:
        positive = sorted(
            distance
            for distance in weekly_distances
            if distance > 0
        )

        if not positive:
            return None

        index = round(
            (len(positive) - 1) * 0.9
        )

        return round(
            positive[index],
            1,
        )

    @staticmethod
    def _recent_load_change(
        weekly_distances: List[float],
    ) -> Optional[float]:
        if len(weekly_distances) < 8:
            return None

        previous = mean(
            weekly_distances[-8:-4]
        )
        recent = mean(
            weekly_distances[-4:]
        )

        if previous <= 0:
            return None

        return round(
            (recent - previous)
            / previous
            * 100,
            1,
        )

    @staticmethod
    def _long_runs_per_month(
        running: List[LongitudinalActivity],
        history_weeks: int,
    ) -> float:
        long_runs = sum(
            activity.distance_km >= 14
            or "longue course"
            in activity.title.lower()
            for activity in running
        )

        months = max(
            history_weeks / 4.345,
            1,
        )

        return round(
            long_runs / months,
            1,
        )

    @staticmethod
    def _secondary_sports(
        activities: List[LongitudinalActivity],
    ) -> List[str]:
        sports = {
            activity.activity_type
            for activity in activities
            if (
                not AthleteProfileBuilder
                ._is_running(activity)
            )
        }

        return sorted(sports)

    @staticmethod
    def _competition_types(
        competitions: List[CompetitionEvent],
    ) -> List[str]:
        types = set()

        for event in competitions:
            if event.distance_km < 7:
                types.add("5_km")
            elif event.distance_km < 15:
                types.add("10_km")
            elif event.distance_km < 25:
                types.add("half_marathon")
            else:
                types.add("long_distance")

        return sorted(types)

    @staticmethod
    def _is_structured_intensity(
        activity: LongitudinalActivity,
    ) -> bool:
        title = activity.title.lower()

        return any(
            keyword in title
            for keyword in {
                "seuil",
                "tempo",
                "vo2",
                "vma",
                "fraction",
            }
        )

    @staticmethod
    def _average(
        values: List[float],
    ) -> float:
        if not values:
            return 0.0

        return mean(values)

    @staticmethod
    def _is_running(
        activity: LongitudinalActivity,
    ) -> bool:
        activity_type = (
            activity.activity_type.lower()
        )

        return (
            "running" in activity_type
            or activity_type
            in {
                "ultrafond",
                "ultra_running",
            }
        )