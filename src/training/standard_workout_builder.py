"""Construction des séances fondamentales Atlas Coach."""

from __future__ import annotations

from datetime import date

from src.performance.athlete_profile import AthleteProfile
from src.performance.models import PerformanceGoal

from .session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    IntensityTarget,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class StandardWorkoutBuilder:
    """Construit les séances qui complètent Atlas Research."""

    def build_endurance(
        self,
        *,
        profile: AthleteProfile,
        workout_date: date,
        duration_minutes: int,
        recovery: bool = False,
    ) -> AdaptiveWorkout:
        """Construit une endurance Z2 ou une récupération."""
        workout_type = (
            WorkoutType.RECOVERY_RUN
            if recovery
            else WorkoutType.ENDURANCE_Z2
        )
        vma = profile.physiological.vma_kmh
        minimum_percent = 55 if recovery else 60
        maximum_percent = 65 if recovery else 75

        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                workout_type,
            ),
            workout_date=workout_date,
            workout_type=workout_type,
            title=(
                "Footing de récupération"
                if recovery
                else "Endurance fondamentale Z2"
            ),
            objective=(
                "Favoriser la récupération active."
                if recovery
                else (
                    "Développer le socle aérobie avec une "
                    "contrainte maîtrisée."
                )
            ),
            blocks=[
                TrainingBlock(
                    name="Course continue facile",
                    block_type=BlockType.CONTINUOUS,
                    duration_minutes=duration_minutes,
                    target=IntensityTarget(
                        zone=1 if recovery else 2,
                        speed_min_kmh=self._vma_speed(
                            vma,
                            minimum_percent,
                        ),
                        speed_max_kmh=self._vma_speed(
                            vma,
                            maximum_percent,
                        ),
                        rpe_0_10=2.5 if recovery else 3.5,
                    ),
                    instructions=(
                        "Rester en aisance respiratoire et ralentir "
                        "si la fréquence cardiaque dérive."
                    ),
                )
            ],
            priority=WorkoutPriority.SUPPORT,
            planned_duration_minutes=duration_minutes,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=(
                    25 if recovery else 40
                ),
                biomechanical_load_0_100=(
                    22 if recovery else 35
                ),
                recovery_min_hours=(
                    8 if recovery else 18
                ),
                recovery_max_hours=(
                    18 if recovery else 30
                ),
                sensitive_structures=[
                    "mollets",
                    "tendons d'Achille",
                ],
            ),
            replacement_types=[
                WorkoutType.CYCLING,
                WorkoutType.REST,
            ],
        )
        workout.validate()
        return workout

    def build_long_run(
        self,
        *,
        profile: AthleteProfile,
        workout_date: date,
        duration_minutes: int,
    ) -> AdaptiveWorkout:
        """Construit une sortie longue aérobie."""
        vma = profile.physiological.vma_kmh
        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.LONG_RUN,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.LONG_RUN,
            title="Sortie longue",
            objective=(
                "Développer l'endurance durable et la tolérance "
                "progressive au volume."
            ),
            blocks=[
                TrainingBlock(
                    name="Endurance longue",
                    block_type=BlockType.CONTINUOUS,
                    duration_minutes=duration_minutes,
                    target=IntensityTarget(
                        zone=2,
                        speed_min_kmh=self._vma_speed(vma, 60),
                        speed_max_kmh=self._vma_speed(vma, 72),
                        rpe_0_10=4,
                    ),
                    instructions=(
                        "Conserver une allure régulière, facile et "
                        "compatible avec une conversation."
                    ),
                )
            ],
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=duration_minutes,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=65,
                biomechanical_load_0_100=65,
                recovery_min_hours=36,
                recovery_max_hours=48,
                sensitive_structures=[
                    "pieds",
                    "mollets",
                    "tendons d'Achille",
                    "genoux",
                    "hanches",
                ],
            ),
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
                WorkoutType.CYCLING,
            ],
        )
        workout.validate()
        return workout

    def build_strength(
        self,
        *,
        workout_date: date,
        duration_minutes: int = 25,
    ) -> AdaptiveWorkout:
        """Construit une séance de renforcement général."""
        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.STRENGTH,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.STRENGTH,
            title="Renforcement du coureur",
            objective=(
                "Développer la force utile, la stabilité et la "
                "tolérance biomécanique."
            ),
            blocks=[
                TrainingBlock(
                    name="Renforcement fonctionnel",
                    block_type=BlockType.STRENGTH,
                    duration_minutes=duration_minutes,
                    target=IntensityTarget(rpe_0_10=6),
                    instructions=(
                        "Travail contrôlé des mollets, quadriceps, "
                        "ischio-jambiers, hanches et tronc."
                    ),
                )
            ],
            sport="strength",
            priority=WorkoutPriority.SUPPORT,
            planned_duration_minutes=duration_minutes,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=45,
                biomechanical_load_0_100=65,
                recovery_min_hours=24,
                recovery_max_hours=48,
                sensitive_structures=[
                    "mollets",
                    "genoux",
                    "hanches",
                    "rachis",
                ],
            ),
            movable=True,
            replacement_types=[WorkoutType.MOBILITY],
        )
        workout.validate()
        return workout

    def build_mobility(
        self,
        *,
        workout_date: date,
        duration_minutes: int = 15,
    ) -> AdaptiveWorkout:
        """Construit une séance courte de mobilité."""
        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.MOBILITY,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.MOBILITY,
            title="Mobilité et entretien",
            objective=(
                "Entretenir les amplitudes utiles et favoriser "
                "la récupération."
            ),
            blocks=[
                TrainingBlock(
                    name="Mobilité active",
                    block_type=BlockType.MOBILITY,
                    duration_minutes=duration_minutes,
                    target=IntensityTarget(rpe_0_10=2),
                    instructions=(
                        "Mobilité douce des chevilles, hanches et "
                        "rachis, sans douleur provoquée."
                    ),
                )
            ],
            sport="mobility",
            priority=WorkoutPriority.OPTIONAL,
            planned_duration_minutes=duration_minutes,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=10,
                biomechanical_load_0_100=15,
                recovery_min_hours=4,
                recovery_max_hours=8,
            ),
            maximum_shift_days=3,
        )
        workout.validate()
        return workout

    def build_race(
        self,
        *,
        goal: PerformanceGoal,
    ) -> AdaptiveWorkout:
        """Construit la séance correspondant à la compétition."""
        duration = (
            goal.target_time_minutes
            or max(20, round(goal.distance_km * 6))
        )
        target_speed = None
        target_pace = None

        if goal.target_time_minutes is not None:
            target_speed = round(
                goal.distance_km
                / (goal.target_time_minutes / 60),
                2,
            )
            target_pace = self._format_pace(
                goal.target_pace_seconds_per_km
            )

        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                goal.event_date,
                WorkoutType.RACE_SPECIFIC,
            ),
            workout_date=goal.event_date,
            workout_type=WorkoutType.RACE_SPECIFIC,
            title=goal.name,
            objective=(
                "Réaliser l'objectif de compétition préparé "
                "par Atlas Coach."
            ),
            blocks=[
                TrainingBlock(
                    name="Compétition",
                    block_type=BlockType.WORK,
                    distance_meters=round(
                        goal.distance_km * 1000
                    ),
                    target=IntensityTarget(
                        pace_min_per_km=target_pace,
                        pace_max_per_km=target_pace,
                        speed_min_kmh=target_speed,
                        speed_max_kmh=target_speed,
                        rpe_0_10=9,
                    ),
                    instructions=(
                        "Respecter la stratégie d'allure définie "
                        "et ajuster selon les sensations du jour."
                    ),
                )
            ],
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=duration,
            planned_distance_km=goal.distance_km,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=95,
                biomechanical_load_0_100=85,
                recovery_min_hours=72,
                recovery_max_hours=120,
                sensitive_structures=[
                    "pieds",
                    "mollets",
                    "tendons d'Achille",
                    "genoux",
                    "hanches",
                ],
            ),
            movable=False,
            maximum_shift_days=0,
            coach_notes=[
                (
                    "Objectif chronométrique : "
                    f"{goal.target_time_minutes} minutes."
                    if goal.target_time_minutes is not None
                    else "Aucun objectif chronométrique déclaré."
                )
            ],
        )
        workout.validate()
        return workout

    @staticmethod
    def _workout_id(
        workout_date: date,
        workout_type: WorkoutType,
    ) -> str:
        return (
            f"{workout_date.isoformat()}-"
            f"{workout_type.value}"
        )

    @staticmethod
    def _vma_speed(
        vma_kmh: float | None,
        percentage: float,
    ) -> float | None:
        if vma_kmh is None:
            return None

        return round(vma_kmh * percentage / 100, 2)

    @staticmethod
    def _format_pace(
        seconds_per_km: int | None,
    ) -> str | None:
        if seconds_per_km is None:
            return None

        minutes, seconds = divmod(seconds_per_km, 60)
        return f"{minutes}:{seconds:02d}"