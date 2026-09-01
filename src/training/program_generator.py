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

from .historical_workout_progression_selector import (
    HistoricalWorkoutPrescription,
    HistoricalWorkoutProgression,
)
from .program_models import (
    AdaptiveTrainingProgram,
    AdaptiveTrainingWeek,
    ProgramGenerationSettings,
    TrainingPhase,
)
from .program_phase_planner import ProgramPhasePlanner
from .program_validator import TrainingProgramValidator
from .research_workout_builder import ResearchWorkoutBuilder
from .session_models import (
    AdaptiveWorkout,
    WorkoutPriority,
    WorkoutType,
)
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
        validator: TrainingProgramValidator | None = None,
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
        self._validator = validator or TrainingProgramValidator()

    def generate(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        start_date: date,
        settings: ProgramGenerationSettings | None = None,
        available_dynamic_metrics: set[str] | None = None,
        historical_progression: (
            HistoricalWorkoutProgression | None
        ) = None,
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
        historical_phase_indices = {
            TrainingPhase.BASE: 0,
            TrainingPhase.DEVELOPMENT: 0,
            TrainingPhase.SPECIFIC: 0,
        }

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
                settings=settings,
                goal=goal,
                week_number=week_number,
                week_start=week_start,
                week_end=week_end,
                training_start=start_date,
                phase=phase,
                quality_cycle_index=quality_cycle_index,
                available_dynamic_metrics=runtime_metrics,
                historical_progression=historical_progression,
                historical_phase_index=historical_phase_indices.get(
                    phase,
                    0,
                ),
            )
            weeks.append(week)

            if used_research:
                quality_cycle_index += 1
                if (
                    historical_progression is not None
                    and phase in historical_phase_indices
                ):
                    historical_phase_indices[phase] += 1

            for workout in week.workouts:
                for note in workout.coach_notes:
                    if (
                        note.startswith("Mesures manquantes")
                        or "expérimental" in note
                    ):
                        warnings.append(
                            f"Semaine {week_number} : {note}"
                        )

        program = AdaptiveTrainingProgram(
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
        validation = self._validator.validate(
            program,
            profile=profile,
        )
        validation.raise_for_errors()
        program.warnings = list(dict.fromkeys([
            *program.warnings,
            *(
                "Contrôle du programme : " + issue.format()
                for issue in validation.warnings
            ),
        ]))
        return program

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
        historical_progression: (
            HistoricalWorkoutProgression | None
        ),
        historical_phase_index: int,
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

            sharpening_days = (
                settings.race_week_sharpening_days_before
            )
            if sharpening_days is not None:
                sharpening_date = (
                    goal.event_date
                    - timedelta(days=sharpening_days)
                )
                if (
                    sharpening_date in dates
                    and sharpening_date not in used_dates
                ):
                    sharpening = (
                        self._standard_builder
                        .build_race_sharpening(
                            profile=profile,
                            goal=goal,
                            workout_date=sharpening_date,
                        )
                    )
                    workouts.append(sharpening)
                    used_dates.add(sharpening_date)

        elif phase != TrainingPhase.RECOVERY:
            prescription = None

            if (
                settings.prioritize_metabolic_quality
                and historical_progression is not None
            ):
                prescription = self._historical_prescription(
                    historical_progression,
                    phase=phase,
                    phase_index=historical_phase_index,
                    week_number=week_number,
                )

            replaces_long_run = bool(
                prescription is not None
                and prescription.kind
                == "long_race_specific"
            )

            if prescription is not None:
                preferred_days = (
                    [settings.preferred_long_run_day]
                    if replaces_long_run
                    else settings.preferred_quality_days
                )
                historical_date = self._preferred_date(
                    dates,
                    preferred_days,
                    used_dates,
                    prefer_latest=replaces_long_run,
                )

                if historical_date is not None:
                    workouts.append(
                        self._build_historical_workout(
                            prescription,
                            profile=profile,
                            goal=goal,
                            workout_date=historical_date,
                        )
                    )
                    used_dates.add(historical_date)
                    used_research = True
            else:
                selection = self._quality_selection(
                    profile=profile,
                    settings=settings,
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

            if (
                phase != TrainingPhase.TAPER
                and not replaces_long_run
            ):
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
                                    settings.maximum_weekly_progression_percent,
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

    @staticmethod
    def _historical_prescription(
        progression: HistoricalWorkoutProgression,
        *,
        phase: TrainingPhase,
        phase_index: int,
        week_number: int,
    ) -> HistoricalWorkoutPrescription | None:
        if (
            phase == TrainingPhase.BASE
            and week_number % 2 == 1
        ):
            return None

        prescriptions = {
            TrainingPhase.BASE: progression.base,
            TrainingPhase.DEVELOPMENT: (
                progression.development
            ),
            TrainingPhase.SPECIFIC: progression.specific,
        }.get(phase, [])

        if not 0 <= phase_index < len(prescriptions):
            return None

        return prescriptions[phase_index]

    def _build_historical_workout(
        self,
        prescription: HistoricalWorkoutPrescription,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        workout_date: date,
    ) -> AdaptiveWorkout:
        if prescription.kind == "short_intervals":
            workout = self._standard_builder.build_short_intervals(
                profile=profile,
                workout_date=workout_date,
                repetitions=prescription.repetitions,
                distance_meters=(
                    prescription.work_distance_meters
                    or 400
                ),
            )
        elif prescription.kind == "threshold_intervals":
            workout = (
                self._standard_builder
                .build_threshold_intervals(
                    profile=profile,
                    workout_date=workout_date,
                    repetitions=prescription.repetitions,
                    distance_meters=(
                        prescription.work_distance_meters
                        or 1000
                    ),
                )
            )
        elif prescription.kind == "mixed_intervals":
            workout = self._standard_builder.build_mixed_intervals(
                profile=profile,
                workout_date=workout_date,
                repetitions=prescription.repetitions,
                threshold_distance_meters=(
                    prescription.threshold_distance_meters
                    or 1000
                ),
                vo2_distance_meters=(
                    prescription.vo2_distance_meters
                    or 400
                ),
            )
        elif prescription.kind == "long_race_specific":
            workout = (
                self._standard_builder
                .build_specific_long_run(
                    profile=profile,
                    goal=goal,
                    workout_date=workout_date,
                    group_distances_meters=list(
                        prescription.group_distances_meters
                    ),
                )
            )
        else:
            raise ValueError(
                "Prescription historique inconnue : "
                f"{prescription.kind}"
            )

        workout.coach_notes.append(
            "Séance sélectionnée depuis une préparation "
            "comparable réussie."
        )
        workout.coach_notes.extend(prescription.reasons)
        if prescription.source_activity_ids:
            workout.coach_notes.append(
                "Sources FIT Atlas : "
                + ", ".join(prescription.source_activity_ids)
                + "."
            )
        return workout

    def _quality_selection(
        self,
        *,
        profile: AthleteProfile,
        settings: ProgramGenerationSettings,
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

        if (
            settings.prioritize_metabolic_quality
            and phase == TrainingPhase.SPECIFIC
        ):
            metabolic = [
                selection
                for selection in selections
                if selection.protocol.workout_type_key
                != "hill_sprints"
            ]
            if metabolic:
                return metabolic[
                    quality_cycle_index % len(metabolic)
                ]

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
        """Ajoute les soutiens sans les placer avant une séance clé."""
        if phase == TrainingPhase.RECOVERY:
            if settings.include_mobility:
                workouts.append(
                    self._standard_builder.build_mobility(
                        workout_date=week_end,
                    )
                )
            return

        if phase == TrainingPhase.RACE_WEEK:
            return

        key_dates = {
            workout.workout_date
            for workout in workouts
            if workout.priority == WorkoutPriority.KEY
        }
        occupied_dates = {
            workout.workout_date
            for workout in workouts
        }
        free_dates = []
        current = week_start

        while current <= week_end:
            if current not in occupied_dates:
                free_dates.append(current)
            current += timedelta(days=1)

        cycling_target = settings.cycling_sessions_per_week
        if phase == TrainingPhase.TAPER:
            cycling_target = 0

        while cycling_target > 0 and free_dates:
            if key_dates:
                cycling_date = max(
                    free_dates,
                    key=lambda candidate: min(
                        abs((candidate - key_date).days)
                        for key_date in key_dates
                    ),
                )
            else:
                cycling_date = free_dates[len(free_dates) // 2]

            workouts.append(
                self._standard_builder.build_cycling(
                    workout_date=cycling_date,
                    duration_minutes=60,
                )
            )
            free_dates.remove(cycling_date)
            cycling_target -= 1

        strength_target = settings.strength_sessions_per_week
        if phase == TrainingPhase.TAPER:
            strength_target = min(strength_target, 1)

        support_types = {
            WorkoutType.ENDURANCE_Z2,
            WorkoutType.RECOVERY_RUN,
            WorkoutType.CYCLING,
        }
        safe_support_dates = sorted({
            workout.workout_date
            for workout in workouts
            if (
                workout.workout_type in support_types
                and (
                    workout.workout_date + timedelta(days=1)
                    not in key_dates
                )
            )
        })

        if len(safe_support_dates) > strength_target:
            safe_support_dates = self._spread_dates(
                safe_support_dates,
                strength_target,
            )

        for workout_date in safe_support_dates[:strength_target]:
            workouts.append(
                self._standard_builder.build_strength(
                    workout_date=workout_date,
                    duration_minutes=20,
                )
            )
    @staticmethod
    def _long_run_duration(
        phase: TrainingPhase,
        week_number: int,
        maximum_progression_percent: float,
    ) -> int:
        """Fait progresser la sortie longue sans dépasser la limite."""
        progression = 1.0 + (
            maximum_progression_percent / 100.0
        )
        progressive_duration = round(
            70 * (progression ** week_number)
        )
        ceilings = {
            TrainingPhase.BASE: 90,
            TrainingPhase.DEVELOPMENT: 95,
            TrainingPhase.SPECIFIC: 105,
        }
        return min(
            ceilings.get(phase, 90),
            progressive_duration,
        )
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
