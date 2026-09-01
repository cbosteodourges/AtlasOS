"""Contrôle structurel universel des programmes Atlas Coach."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re

from src.performance.athlete_profile import AthleteProfile

from .program_models import AdaptiveTrainingProgram, TrainingPhase
from .session_models import BlockType, WorkoutPriority, WorkoutType


@dataclass(frozen=True, slots=True)
class ProgramValidationIssue:
    """Anomalie localisée et exploitable avant publication."""

    severity: str
    code: str
    message: str
    week_number: int | None = None
    workout_id: str | None = None

    def format(self) -> str:
        location = []
        if self.week_number is not None:
            location.append(f"semaine {self.week_number}")
        if self.workout_id:
            location.append(f"séance {self.workout_id}")
        suffix = f" ({', '.join(location)})" if location else ""
        return f"{self.code}: {self.message}{suffix}"


@dataclass(slots=True)
class ProgramValidationReport:
    """Résultat complet du contrôle, sans masquer les avertissements."""

    issues: list[ProgramValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ProgramValidationIssue]:
        return [item for item in self.issues if item.severity == "error"]

    @property
    def warnings(self) -> list[ProgramValidationIssue]:
        return [item for item in self.issues if item.severity == "warning"]

    @property
    def valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            details = "\n".join(f"- {item.format()}" for item in self.errors)
            raise ProgramValidationError(
                "Programme refusé avant publication :\n" + details
            )


class ProgramValidationError(ValueError):
    """Programme incohérent qui ne doit jamais être publié."""


class TrainingProgramValidator:
    """Vérifie les invariants indépendants de la distance préparée."""

    _STRUCTURED_TITLE = re.compile(
        r"(?:\d+\s*[×x]\s*\d+|\d+\s+à\s+\d+\s+répétitions|"
        r"répétitions|lignes?\s+droites?)",
        re.IGNORECASE,
    )
    _INTENSE_TYPES = {
        WorkoutType.THRESHOLD_SV2,
        WorkoutType.VMA_SHORT,
        WorkoutType.VMA_LONG,
        WorkoutType.HILL_SPRINTS,
        WorkoutType.MIXED_THRESHOLD_VO2,
        WorkoutType.TRIANGULAR_VO2,
        WorkoutType.RACE_SPECIFIC,
    }

    def validate(
        self,
        program: AdaptiveTrainingProgram,
        *,
        profile: AthleteProfile | None = None,
    ) -> ProgramValidationReport:
        report = ProgramValidationReport()
        self._validate_program_frame(program, report)
        self._validate_weeks(program, report)
        self._validate_race(program, report)
        if profile is not None:
            self._validate_profile_constraints(program, profile, report)
        return report

    def _issue(
        self,
        report: ProgramValidationReport,
        severity: str,
        code: str,
        message: str,
        *,
        week_number: int | None = None,
        workout_id: str | None = None,
    ) -> None:
        report.issues.append(
            ProgramValidationIssue(
                severity, code, message, week_number, workout_id
            )
        )

    def _validate_program_frame(
        self,
        program: AdaptiveTrainingProgram,
        report: ProgramValidationReport,
    ) -> None:
        if not program.weeks:
            self._issue(report, "error", "PROGRAM_EMPTY", "aucune semaine")
        if program.start_date > program.end_date:
            self._issue(
                report, "error", "PROGRAM_DATES", "la fin précède le début"
            )
        if program.goal.event_date != program.end_date:
            self._issue(
                report,
                "error",
                "EVENT_DATE",
                "la date de fin ne correspond pas à la compétition",
            )

    def _validate_weeks(
        self,
        program: AdaptiveTrainingProgram,
        report: ProgramValidationReport,
    ) -> None:
        identifiers: set[str] = set()
        previous_end: date | None = None
        previous_number = 0

        for week in program.weeks:
            if week.week_number <= previous_number:
                self._issue(
                    report,
                    "error",
                    "WEEK_ORDER",
                    "numérotation non strictement croissante",
                    week_number=week.week_number,
                )
            if week.start_date > week.end_date:
                self._issue(
                    report,
                    "error",
                    "WEEK_DATES",
                    "la fin de semaine précède son début",
                    week_number=week.week_number,
                )
            if previous_end is not None and week.start_date <= previous_end:
                self._issue(
                    report,
                    "error",
                    "WEEK_OVERLAP",
                    "chevauchement entre deux semaines",
                    week_number=week.week_number,
                )
            if week.end_date > program.end_date:
                self._issue(
                    report,
                    "error",
                    "WEEK_AFTER_EVENT",
                    "semaine située après la compétition",
                    week_number=week.week_number,
                )

            intense_dates: list[date] = []
            for workout in week.workouts:
                self._validate_workout(program, week, workout, report)
                if workout.workout_id in identifiers:
                    self._issue(
                        report,
                        "error",
                        "DUPLICATE_WORKOUT_ID",
                        "identifiant de séance dupliqué",
                        week_number=week.week_number,
                        workout_id=workout.workout_id,
                    )
                identifiers.add(workout.workout_id)
                if (
                    workout.priority == WorkoutPriority.KEY
                    and workout.workout_type in self._INTENSE_TYPES
                ):
                    intense_dates.append(workout.workout_date)

            if program.settings.avoid_consecutive_intense_days:
                ordered = sorted(set(intense_dates))
                if any(
                    (right - left).days == 1
                    for left, right in zip(ordered, ordered[1:])
                ):
                    self._issue(
                        report,
                        "warning",
                        "CONSECUTIVE_INTENSITY",
                        "deux séances intenses sont placées deux jours consécutifs",
                        week_number=week.week_number,
                    )

            previous_end = week.end_date
            previous_number = week.week_number

    def _validate_workout(self, program, week, workout, report) -> None:
        context = {
            "week_number": week.week_number,
            "workout_id": workout.workout_id,
        }
        if not week.start_date <= workout.workout_date <= week.end_date:
            self._issue(
                report,
                "error",
                "WORKOUT_OUTSIDE_WEEK",
                "date hors de sa semaine",
                **context,
            )
        if not program.start_date <= workout.workout_date <= program.end_date:
            self._issue(
                report,
                "error",
                "WORKOUT_OUTSIDE_PROGRAM",
                "date hors du programme actif",
                **context,
            )

        try:
            workout.validate()
        except (TypeError, ValueError) as error:
            self._issue(
                report,
                "error",
                "WORKOUT_SCHEMA",
                str(error),
                **context,
            )
            return

        work_blocks = [
            block for block in workout.blocks
            if block.block_type == BlockType.WORK
        ]
        if self._STRUCTURED_TITLE.search(workout.title) and not work_blocks:
            self._issue(
                report,
                "error",
                "TITLE_WITHOUT_STRUCTURE",
                "le titre annonce des répétitions absentes des blocs",
                **context,
            )

        for block in workout.blocks:
            target = block.target
            for minimum_name, maximum_name, label in (
                ("speed_min_kmh", "speed_max_kmh", "vitesse"),
                ("heart_rate_min_bpm", "heart_rate_max_bpm", "fréquence cardiaque"),
                ("power_min_watts", "power_max_watts", "puissance"),
                ("gradient_min_percent", "gradient_max_percent", "pente"),
            ):
                minimum = getattr(target, minimum_name)
                maximum = getattr(target, maximum_name)
                if (
                    minimum is not None
                    and maximum is not None
                    and minimum > maximum
                ):
                    self._issue(
                        report,
                        "error",
                        "TARGET_RANGE",
                        f"bornes de {label} inversées dans « {block.name} »",
                        **context,
                    )
            if (
                block.block_type == BlockType.WORK
                and block.repetitions > 1
                and not block.recovery_minutes
            ):
                self._issue(
                    report,
                    "warning",
                    "RECOVERY_UNSPECIFIED",
                    f"récupération non précisée pour « {block.name} »",
                    **context,
                )

        planned = workout.planned_duration_minutes
        computed = sum(
            block.estimated_duration_minutes for block in workout.blocks
        )
        if planned and computed and computed > planned + 5:
            self._issue(
                report,
                "error",
                "DURATION_UNDERESTIMATED",
                (
                    f"les blocs durent au moins {computed:.1f} min "
                    f"pour {planned} min annoncées"
                ),
                **context,
            )
        elif planned and computed and abs(planned - computed) > 15:
            self._issue(
                report,
                "warning",
                "DURATION_AMBIGUOUS",
                (
                    f"{planned} min annoncées contre "
                    f"{computed:.1f} min structurées"
                ),
                **context,
            )

    def _validate_race(
        self,
        program: AdaptiveTrainingProgram,
        report: ProgramValidationReport,
    ) -> None:
        races = [
            workout
            for week in program.weeks
            for workout in week.workouts
            if workout.workout_type == WorkoutType.RACE_SPECIFIC
        ]
        if len(races) != 1:
            self._issue(
                report,
                "error",
                "RACE_COUNT",
                f"{len(races)} compétition(s) trouvée(s), une seule attendue",
            )
            return

        race = races[0]
        if race.workout_date != program.goal.event_date:
            self._issue(
                report,
                "error",
                "RACE_DATE",
                "la compétition n'est pas placée le jour de l'objectif",
                workout_id=race.workout_id,
            )
        if (
            race.planned_distance_km is None
            or abs(race.planned_distance_km - program.goal.distance_km) > 0.05
        ):
            self._issue(
                report,
                "error",
                "RACE_DISTANCE",
                "la distance de compétition ne correspond pas à l'objectif",
                workout_id=race.workout_id,
            )

    def _validate_profile_constraints(
        self,
        program: AdaptiveTrainingProgram,
        profile: AthleteProfile,
        report: ProgramValidationReport,
    ) -> None:
        available = profile.availability.available_days_per_week
        if available:
            for week in program.weeks:
                if week.running_workout_count > available:
                    self._issue(
                        report,
                        "error",
                        "AVAILABILITY_EXCEEDED",
                        (
                            f"{week.running_workout_count} séances de course "
                            f"pour {available} jour(s) disponible(s)"
                        ),
                        week_number=week.week_number,
                    )

        if profile.current_pain_or_injury and program.weeks:
            first = program.weeks[0]
            if (
                first.phase != TrainingPhase.RECOVERY
                or first.running_workout_count
            ):
                self._issue(
                    report,
                    "error",
                    "ACTIVE_PAIN_NOT_PROTECTED",
                    "la première semaine ne protège pas une douleur active",
                    week_number=first.week_number,
                )
