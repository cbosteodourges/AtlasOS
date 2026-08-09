"""Génération du programme périodisé Atlas Coach."""

from __future__ import annotations

from datetime import date, timedelta

from src.performance.athlete_profile import AthleteProfile
from src.performance.models import PerformanceGoal
from src.research.training_protocol_catalog import (
    build_default_training_protocol_registry,
)
from src.research.training_protocol_selector import (
    ProtocolSelection,
    TrainingProtocolSelector,
)

from .program_models import (
    AdaptiveTrainingProgram,
    AdaptiveTrainingWeek,
    ProgramGenerationSettings,
    TrainingPhase,
)
from .program_phase_planner import ProgramPhasePlanner
from .research_workout_builder import ResearchWorkoutBuilder
from .session_models import AdaptiveWorkout
from .standard_workout_builder import StandardWorkoutBuilder


class TrainingProgramGenerator:
    """Assemble profil, objectif, recherche et périodisation."""

    DAY_INDEX = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    def __init__(
        self,
        *,
        phase_planner: ProgramPhasePlanner | None = None,
        protocol_selector: TrainingProtocolSelector | None = None,
        research_builder: ResearchWorkoutBuilder | None = None,
        standard_builder: StandardWorkoutBuilder | None = None,
    ) -> None:
        self._phase_planner = (
            phase_planner or ProgramPhasePlanner()
        )
        self._protocol_selector = (
            protocol_selector
            or TrainingProtocolSelector(
                build_default_training_protocol_registry()
            )
        )
        self._research_builder = (
            research_builder or ResearchWorkoutBuilder()
        )
        self._standard_builder = (
            standard_builder or StandardWorkoutBuilder()
        )

    def generate(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        start_date: date,
        settings: ProgramGenerationSettings | None = None,
        available_dynamic_metrics: set[str] | None = None,
    ) -> AdaptiveTrainingProgram:
        """Génère le programme complet jusqu’à la compétition."""
        settings = settings or ProgramGenerationSettings()
        settings.validate()

        runtime_metrics = set(
            available_dynamic_metrics or set()
        )
        runtime_metrics.add("recovery_status")

        phase_plan = self._phase_planner.plan(
            start_date=start_date,
            event_date=goal.event_date,
        )
        weeks = []
        warnings = []
        quality_cycle_index = 0

        if profile.current_pain_or_injury:
            warnings.append(
                "Douleur ou blessure active : la première semaine "
                "est convertie en phase de récupération."
            )

        if profile.medical_constraints:
            warnings.append(
                "Contraintes médicales à prendre en compte : "
                + ", ".join(profile.medical_constraints)
                + "."
            )

        calendar_start = start_date - timedelta(
            days=start_date.weekday()
        )

        for index, planned_phase in enumerate(
            phase_plan.phases
        ):
            week_number = index + 1
            week_start = calendar_start + timedelta(
                days=index * 7
            )
            week_end = min(
                week_start + timedelta(days=6),
                goal.event_date,
            )
            phase = planned_phase

            if (
                profile.current_pain_or_injury
                and week_number == 1
                and phase != TrainingPhase.RACE_WEEK
            ):
                phase = TrainingPhase.RECOVERY

            week, used_research = self._build_week(
                profile=profile,
                goal=goal,
                settings=settings,
                week_number=week_number,
                week_start=week_start,
                week_end=week_end,
                training_start=start_date,
                phase=phase,
                quality_cycle_index=quality_cycle_index,
                available_dynamic_metrics=runtime_metrics,
            )
            weeks.append(week)

            if used_research:
                quality_cycle_index += 1

            for workout in week.workouts:
                for note in workout.coach_notes:
                    if (
                        note.startswith("Mesures manquantes")
                        or "expérimental" in note
                    ):
                        warnings.append(
                            f"Semaine {week_number} : {note}"
                        )

        return AdaptiveTrainingProgram(
            athlete_id=profile.athlete_id,
            goal=goal,
            created_at=date.today(),
            start_date=start_date,
            end_date=goal.event_date,
            settings=settings,
            weeks=weeks,
            explanation=(
                "Programme périodisé à partir du profil longitudinal, "
                "des tolérances apprises et du registre Atlas Research."
            ),
            warnings=list(dict.fromkeys(warnings)),
        )

    def _build_week(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        settings: ProgramGenerationSettings,
        week_number: int,
        week_start: date,
        week_end: date,
        training_start: date,
        phase: TrainingPhase,
        quality_cycle_index: int,
        available_dynamic_metrics: set[str],
    ) -> tuple[AdaptiveTrainingWeek, bool]:
        dates = self._available_dates(
            max(week_start, training_start),
            week_end,
            profile,
        )
        workouts: list[AdaptiveWorkout] = []
        used_dates: set[date] = set()
        used_research = False

        if phase == TrainingPhase.RACE_WEEK:
            race = self._standard_builder.build_race(
                goal=goal
            )
            workouts.append(race)
            used_dates.add(race.workout_date)

        elif phase != TrainingPhase.RECOVERY:
            selection = self._quality_selection(
                profile=profile,
                goal=goal,
                phase=phase,
                week_number=week_number,
                quality_cycle_index=quality_cycle_index,
                available_dynamic_metrics=(
                    available_dynamic_metrics
                ),
            )

            if selection is not None:
                quality_date = self._preferred_date(
                    dates,
                    settings.preferred_quality_days,
                    used_dates,
                )

                if quality_date is not None:
                    workouts.append(
                        self._research_builder.build(
                            selection=selection,
                            profile=profile,
                            workout_date=quality_date,
                        )
                    )
                    used_dates.add(quality_date)
                    used_research = True

            if phase != TrainingPhase.TAPER:
                long_date = self._preferred_date(
                    dates,
                    [settings.preferred_long_run_day],
                    used_dates,
                    prefer_latest=True,
                )

                if long_date is not None:
                    workouts.append(
                        self._standard_builder.build_long_run(
                            profile=profile,
                            workout_date=long_date,
                            duration_minutes=(
                                self._long_run_duration(
                                    phase,
                                    week_number,
                                )
                            ),
                        )
                    )
                    used_dates.add(long_date)

        running_target = self._running_session_target(
            profile,
            settings,
            phase,
        )
        running_count = sum(
            workout.sport == "running"
            for workout in workouts
        )

        remaining_dates = [
            workout_date
            for workout_date in dates
            if workout_date not in used_dates
        ]
        needed_running_sessions = max(
            0,
            running_target - running_count,
        )
        easy_dates = self._spread_dates(
            remaining_dates,
            needed_running_sessions,
        )

        for workout_date in easy_dates:
            recovery = phase in {
                TrainingPhase.RECOVERY,
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            }
            workouts.append(
                self._standard_builder.build_endurance(
                    profile=profile,
                    workout_date=workout_date,
                    duration_minutes=(
                        30 if recovery else 45
                    ),
                    recovery=recovery,
                )
            )
            used_dates.add(workout_date)
            running_count += 1

        self._add_support_sessions(
            workouts=workouts,
            week_start=max(
                week_start,
                training_start,
            ),
            week_end=week_end,
            settings=settings,
            phase=phase,
        )
        workouts.sort(key=lambda item: item.workout_date)

        return (
            AdaptiveTrainingWeek(
                week_number=week_number,
                start_date=week_start,
                end_date=week_end,
                phase=phase,
                objective=self._phase_objective(phase),
                workouts=workouts,
                target_duration_minutes=sum(
                    workout.estimated_duration_minutes
                    for workout in workouts
                ),
                is_recovery_week=phase in {
                    TrainingPhase.RECOVERY,
                    TrainingPhase.TAPER,
                },
                coach_notes=[
                    (
                        "Semaine construite avec Atlas Research."
                        if used_research
                        else (
                            "Semaine fondamentale sans protocole "
                            "intense Atlas Research."
                        )
                    )
                ],
            ),
            used_research,
        )

    def _quality_selection(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        phase: TrainingPhase,
        week_number: int,
        quality_cycle_index: int,
        available_dynamic_metrics: set[str],
    ) -> ProtocolSelection | None:
        if phase not in {
            TrainingPhase.BASE,
            TrainingPhase.DEVELOPMENT,
            TrainingPhase.SPECIFIC,
        }:
            return None

        if (
            phase == TrainingPhase.BASE
            and week_number % 2 == 1
        ):
            return None

        selections = self._protocol_selector.select(
            profile=profile,
            phase=phase.value,
            goal_distance_km=goal.distance_km,
            available_dynamic_metrics=(
                available_dynamic_metrics
            ),
        )

        if not selections:
            return None

        return selections[
            quality_cycle_index % len(selections)
        ]

    def _available_dates(
        self,
        week_start: date,
        week_end: date,
        profile: AthleteProfile,
    ) -> list[date]:
        unavailable = {
            day.lower()
            for day in profile.availability.unavailable_days
        }
        preferred = {
            day.lower()
            for day
            in profile.availability.preferred_training_days
        }
        dates = []
        current = week_start

        while current <= week_end:
            day_name = self._day_name(current)

            if day_name not in unavailable and (
                not preferred or day_name in preferred
            ):
                dates.append(current)

            current += timedelta(days=1)

        return dates

    @staticmethod
    def _spread_dates(
        dates: list[date],
        count: int,
    ) -> list[date]:
        """Répartit les séances faciles sur les jours libres."""
        if count <= 0 or not dates:
            return []

        if count >= len(dates):
            return list(dates)

        if count == 1:
            return [dates[len(dates) // 2]]

        last_index = len(dates) - 1
        indices = [
            round(index * last_index / (count - 1))
            for index in range(count)
        ]

        return [
            dates[index]
            for index in dict.fromkeys(indices)
        ]

    def _preferred_date(
        self,
        dates: list[date],
        preferred_days: list[str],
        used_dates: set[date],
        *,
        prefer_latest: bool = False,
    ) -> date | None:
        candidates = [
            item
            for item in dates
            if item not in used_dates
        ]
        preferred = [
            item.lower()
            for item in preferred_days
        ]

        for day_name in preferred:
            for candidate in candidates:
                if self._day_name(candidate) == day_name:
                    return candidate

        if not candidates:
            return None

        return (
            candidates[-1]
            if prefer_latest
            else candidates[0]
        )

    @staticmethod
    def _running_session_target(
        profile: AthleteProfile,
        settings: ProgramGenerationSettings,
        phase: TrainingPhase,
    ) -> int:
        target = settings.running_sessions_per_week
        available = (
            profile.availability.available_days_per_week
        )

        if available is not None:
            target = min(target, available)

        if phase == TrainingPhase.RECOVERY:
            if profile.current_pain_or_injury:
                return 0
            return min(target, 2)
        if phase == TrainingPhase.TAPER:
            return min(target, 3)
        if phase == TrainingPhase.RACE_WEEK:
            return min(target, 3)

        return target

    def _add_support_sessions(
        self,
        *,
        workouts: list[AdaptiveWorkout],
        week_start: date,
        week_end: date,
        settings: ProgramGenerationSettings,
        phase: TrainingPhase,
    ) -> None:
        # Les activités de soutien sont normalement ajoutées
        # à la demande depuis le calendrier Atlas Coach.
        if (
            phase == TrainingPhase.RECOVERY
            and settings.include_mobility
        ):
            workouts.append(
                self._standard_builder.build_mobility(
                    workout_date=week_end,
                )
            )
        return

    @staticmethod
    def _long_run_duration(
        phase: TrainingPhase,
        week_number: int,
    ) -> int:
        if phase == TrainingPhase.BASE:
            return min(90, 70 + week_number * 5)
        if phase == TrainingPhase.DEVELOPMENT:
            return 95
        return 105

    @staticmethod
    def _phase_objective(
        phase: TrainingPhase,
    ) -> str:
        objectives = {
            TrainingPhase.BASE: (
                "Construire le socle aérobie et biomécanique."
            ),
            TrainingPhase.DEVELOPMENT: (
                "Développer progressivement les qualités ciblées."
            ),
            TrainingPhase.SPECIFIC: (
                "Rapprocher les séances des exigences de l’objectif."
            ),
            TrainingPhase.TAPER: (
                "Réduire la fatigue tout en conservant de l’activation."
            ),
            TrainingPhase.RACE_WEEK: (
                "Arriver disponible et réaliser la compétition."
            ),
            TrainingPhase.RECOVERY: (
                "Favoriser la récupération et réévaluer la douleur."
            ),
        }
        return objectives[phase]

    @classmethod
    def _day_name(cls, value: date) -> str:
        return next(
            name
            for name, index in cls.DAY_INDEX.items()
            if index == value.weekday()
        )
