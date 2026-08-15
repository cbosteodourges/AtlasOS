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
        minimum_percent = 63 if recovery else 68
        maximum_percent = 68 if recovery else 72

        threshold_heart_rate = (
            profile.physiological.threshold_heart_rate_bpm
            or profile.physiological.sv2.heart_rate_bpm
        )
        maximum_heart_rate = (
            profile.physiological.maximum_heart_rate_bpm
        )

        if threshold_heart_rate is not None:
            heart_rate_min = round(
                threshold_heart_rate
                * (0.66 if recovery else 0.75)
            )
            heart_rate_max = round(
                threshold_heart_rate
                * (0.75 if recovery else 0.86)
            )
        elif maximum_heart_rate is not None:
            heart_rate_min = round(
                maximum_heart_rate
                * (0.57 if recovery else 0.65)
            )
            heart_rate_max = round(
                maximum_heart_rate
                * (0.65 if recovery else 0.75)
            )
        else:
            heart_rate_min = None
            heart_rate_max = None

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
                        heart_rate_min_bpm=heart_rate_min,
                    heart_rate_max_bpm=heart_rate_max,
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

    def build_cycling(
        self,
        *,
        workout_date: date,
        duration_minutes: int = 60,
    ) -> AdaptiveWorkout:
        """Construit une séance de vélo en endurance aérobie."""
        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.CYCLING,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.CYCLING,
            title="Vélo endurance croisée",
            objective=(
                "Entretenir le volume aérobie avec une contrainte "
                "mécanique réduite pour la course."
            ),
            blocks=[
                TrainingBlock(
                    name="Endurance continue à vélo",
                    block_type=BlockType.CONTINUOUS,
                    duration_minutes=duration_minutes,
                    target=IntensityTarget(
                        zone=2,
                        rpe_0_10=3.5,
                    ),
                    instructions=(
                        "Pédalage souple et régulier, respiration "
                        "facile, sans rechercher la puissance."
                    ),
                )
            ],
            sport="cycling",
            priority=WorkoutPriority.SUPPORT,
            planned_duration_minutes=duration_minutes,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=40,
                biomechanical_load_0_100=20,
                recovery_min_hours=12,
                recovery_max_hours=24,
                sensitive_structures=[
                    "quadriceps",
                    "hanches",
                ],
            ),
            movable=True,
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
                WorkoutType.RECOVERY_RUN,
            ],
            coach_notes=[
                (
                    "Séance croisée retenue grâce à la tolérance "
                    "observée dans l'historique individuel."
                )
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

    def build_short_intervals(
        self,
        *,
        profile: AthleteProfile,
        workout_date: date,
        repetitions: int,
        distance_meters: int = 400,
    ) -> AdaptiveWorkout:
        """Construit une séance courte VMA issue de l'historique."""
        vma = profile.physiological.vma_kmh
        minimum_speed = self._vma_speed(vma, 95)
        maximum_speed = self._vma_speed(vma, 100)

        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.VMA_SHORT,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.VMA_SHORT,
            title=f"{repetitions} × {distance_meters} m VO₂max",
            objective=(
                "Développer la VO₂max avec une structure "
                "historiquement bien tolérée."
            ),
            blocks=[
                TrainingBlock(
                    name="Échauffement progressif",
                    block_type=BlockType.WARM_UP,
                    duration_minutes=20,
                    target=IntensityTarget(
                        zone=2,
                        rpe_0_10=3,
                    ),
                ),
                TrainingBlock(
                    name=(
                        f"{repetitions} × {distance_meters} m"
                    ),
                    block_type=BlockType.WORK,
                    repetitions=repetitions,
                    distance_meters=distance_meters,
                    recovery_minutes=1,
                    target=IntensityTarget(
                        zone=4,
                        speed_min_kmh=minimum_speed,
                        speed_max_kmh=maximum_speed,
                        rpe_0_10=8,
                    ),
                    instructions=(
                        "Courir régulièrement sans sprint final ; "
                        "récupération active entre les répétitions."
                    ),
                ),
                TrainingBlock(
                    name="Retour au calme",
                    block_type=BlockType.COOL_DOWN,
                    duration_minutes=10,
                    target=IntensityTarget(
                        zone=1,
                        rpe_0_10=2,
                    ),
                ),
            ],
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=55,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=72,
                biomechanical_load_0_100=65,
                recovery_min_hours=36,
                recovery_max_hours=48,
            ),
            movable=True,
            maximum_shift_days=1,
            replacement_types=[WorkoutType.ENDURANCE_Z2],
            coach_notes=[
                "Structure apprise depuis les séances FIT réussies.",
                "Réévaluation Wellness obligatoire le jour même.",
            ],
        )
        workout.validate()
        return workout

    def build_threshold_intervals(
        self,
        *,
        profile: AthleteProfile,
        workout_date: date,
        repetitions: int,
        distance_meters: int = 1000,
    ) -> AdaptiveWorkout:
        """Construit des répétitions longues autour du SV2."""
        physiological = profile.physiological
        reference_speed = (
            physiological.threshold_speed_kmh
            or physiological.sv2.speed_kmh
        )
        minimum_speed = (
            round(reference_speed * 0.98, 2)
            if reference_speed is not None
            else self._vma_speed(
                physiological.vma_kmh,
                90,
            )
        )
        maximum_speed = (
            round(reference_speed * 1.02, 2)
            if reference_speed is not None
            else self._vma_speed(
                physiological.vma_kmh,
                94,
            )
        )
        threshold_hr = (
            physiological.threshold_heart_rate_bpm
            or physiological.sv2.heart_rate_bpm
        )

        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.THRESHOLD_SV2,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.THRESHOLD_SV2,
            title=f"{repetitions} × {distance_meters} m au SV2",
            objective=(
                "Développer la vitesse soutenable au seuil "
                "selon les séances historiquement efficaces."
            ),
            blocks=[
                TrainingBlock(
                    name="Échauffement progressif",
                    block_type=BlockType.WARM_UP,
                    duration_minutes=20,
                    target=IntensityTarget(
                        zone=2,
                        rpe_0_10=3,
                    ),
                ),
                TrainingBlock(
                    name=(
                        f"{repetitions} × {distance_meters} m "
                        "au seuil"
                    ),
                    block_type=BlockType.WORK,
                    repetitions=repetitions,
                    distance_meters=distance_meters,
                    recovery_minutes=2,
                    target=IntensityTarget(
                        zone=3,
                        speed_min_kmh=minimum_speed,
                        speed_max_kmh=maximum_speed,
                        heart_rate_min_bpm=(
                            round(threshold_hr * 0.94)
                            if threshold_hr is not None
                            else None
                        ),
                        heart_rate_max_bpm=threshold_hr,
                        rpe_0_10=7,
                    ),
                    instructions=(
                        "Rester proche du SV2 sans accélérer "
                        "au-delà de la cible."
                    ),
                ),
                TrainingBlock(
                    name="Retour au calme",
                    block_type=BlockType.COOL_DOWN,
                    duration_minutes=10,
                    target=IntensityTarget(
                        zone=1,
                        rpe_0_10=2,
                    ),
                ),
            ],
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=65,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=75,
                biomechanical_load_0_100=62,
                recovery_min_hours=36,
                recovery_max_hours=48,
            ),
            movable=True,
            maximum_shift_days=1,
            replacement_types=[WorkoutType.ENDURANCE_Z2],
            coach_notes=[
                "Structure apprise depuis les séances FIT réussies.",
                "Réévaluation Wellness obligatoire le jour même.",
            ],
        )
        workout.validate()
        return workout

    def build_mixed_intervals(
        self,
        *,
        profile: AthleteProfile,
        workout_date: date,
        repetitions: int = 4,
        threshold_distance_meters: int = 1000,
        vo2_distance_meters: int = 400,
    ) -> AdaptiveWorkout:
        """Construit des séries alternant SV2 et VO₂max."""
        physiological = profile.physiological
        threshold_speed = (
            physiological.threshold_speed_kmh
            or physiological.sv2.speed_kmh
            or self._vma_speed(
                physiological.vma_kmh,
                92,
            )
        )
        vma_min = self._vma_speed(
            physiological.vma_kmh,
            95,
        )
        vma_max = self._vma_speed(
            physiological.vma_kmh,
            100,
        )
        blocks = [
            TrainingBlock(
                name="Échauffement progressif",
                block_type=BlockType.WARM_UP,
                duration_minutes=20,
                target=IntensityTarget(
                    zone=2,
                    rpe_0_10=3,
                ),
            )
        ]

        for index in range(1, repetitions + 1):
            blocks.extend([
                TrainingBlock(
                    name=(
                        f"Série {index} — "
                        f"{threshold_distance_meters} m SV2"
                    ),
                    block_type=BlockType.WORK,
                    distance_meters=threshold_distance_meters,
                    recovery_minutes=1,
                    target=IntensityTarget(
                        zone=3,
                        speed_min_kmh=threshold_speed,
                        speed_max_kmh=threshold_speed,
                        rpe_0_10=7,
                    ),
                ),
                TrainingBlock(
                    name=(
                        f"Série {index} — "
                        f"{vo2_distance_meters} m VO₂max"
                    ),
                    block_type=BlockType.WORK,
                    distance_meters=vo2_distance_meters,
                    recovery_minutes=2,
                    target=IntensityTarget(
                        zone=4,
                        speed_min_kmh=vma_min,
                        speed_max_kmh=vma_max,
                        rpe_0_10=8,
                    ),
                ),
            ])

        blocks.append(
            TrainingBlock(
                name="Retour au calme",
                block_type=BlockType.COOL_DOWN,
                duration_minutes=10,
                target=IntensityTarget(
                    zone=1,
                    rpe_0_10=2,
                ),
            )
        )

        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.MIXED_THRESHOLD_VO2,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.MIXED_THRESHOLD_VO2,
            title=(
                f"{repetitions} × "
                f"({threshold_distance_meters} m SV2 + "
                f"{vo2_distance_meters} m VO₂max)"
            ),
            objective=(
                "Associer seuil et VO₂max selon une structure "
                "déjà utilisée dans les préparations réussies."
            ),
            blocks=blocks,
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=70,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=82,
                biomechanical_load_0_100=70,
                recovery_min_hours=48,
                recovery_max_hours=60,
            ),
            movable=True,
            maximum_shift_days=1,
            replacement_types=[
                WorkoutType.THRESHOLD_SV2,
                WorkoutType.ENDURANCE_Z2,
            ],
            coach_notes=[
                "Structure mixte apprise depuis l'historique FIT.",
                "Réévaluation Wellness obligatoire le jour même.",
            ],
        )
        workout.validate()
        return workout

    def build_specific_long_run(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        workout_date: date,
        group_distances_meters: list[int],
    ) -> AdaptiveWorkout:
        """Construit une sortie longue avec blocs à allure objectif."""
        target_speed = (
            round(
                goal.distance_km
                / (goal.target_time_minutes / 60),
                2,
            )
            if goal.target_time_minutes is not None
            else self._vma_speed(
                profile.physiological.vma_kmh,
                82,
            )
        )
        target_pace = (
            self._format_pace(round(3600 / target_speed))
            if target_speed is not None
            else None
        )
        blocks = [
            TrainingBlock(
                name="Mise en route en Z2",
                block_type=BlockType.WARM_UP,
                distance_meters=3000,
                target=IntensityTarget(
                    zone=2,
                    rpe_0_10=3,
                ),
            )
        ]

        for index, distance_meters in enumerate(
            group_distances_meters,
            start=1,
        ):
            blocks.append(
                TrainingBlock(
                    name=(
                        f"Bloc spécifique {index} — "
                        f"{distance_meters} m"
                    ),
                    block_type=BlockType.WORK,
                    distance_meters=distance_meters,
                    target=IntensityTarget(
                        zone=3,
                        pace_min_per_km=target_pace,
                        pace_max_per_km=target_pace,
                        speed_min_kmh=target_speed,
                        speed_max_kmh=target_speed,
                        rpe_0_10=6,
                    ),
                    instructions=(
                        "Tenir l'allure semi avec une foulée "
                        "relâchée et régulière."
                    ),
                )
            )
            if index < len(group_distances_meters):
                blocks.append(
                    TrainingBlock(
                        name="Récupération en Z2",
                        block_type=BlockType.RECOVERY,
                        distance_meters=1000,
                        target=IntensityTarget(
                            zone=2,
                            rpe_0_10=3,
                        ),
                    )
                )

        blocks.append(
            TrainingBlock(
                name="Retour au calme",
                block_type=BlockType.COOL_DOWN,
                distance_meters=2000,
                target=IntensityTarget(
                    zone=1,
                    rpe_0_10=2,
                ),
            )
        )
        planned_distance = (
            sum(group_distances_meters)
            + 5000
            + max(0, len(group_distances_meters) - 1)
            * 1000
        ) / 1000

        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.LONG_RUN,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.LONG_RUN,
            title="Sortie longue spécifique semi",
            objective=(
                "Développer l'endurance spécifique à l'allure "
                "objectif selon les préparations réussies."
            ),
            blocks=blocks,
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=round(
                planned_distance * 5.8
            ),
            planned_distance_km=planned_distance,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=85,
                biomechanical_load_0_100=78,
                recovery_min_hours=48,
                recovery_max_hours=72,
            ),
            movable=True,
            maximum_shift_days=1,
            replacement_types=[WorkoutType.LONG_RUN],
            coach_notes=[
                "Blocs spécifiques issus de l'historique FIT.",
                "Cette séance remplace toute autre intensité majeure.",
                "Réévaluation Wellness obligatoire le jour même.",
            ],
        )
        workout.validate()
        return workout

    def build_race_sharpening(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        workout_date: date,
    ) -> AdaptiveWorkout:
        """Construit un rappel court à l'allure spécifique."""

        target_speed = (
            round(
                goal.distance_km
                / (goal.target_time_minutes / 60),
                2,
            )
            if goal.target_time_minutes is not None
            else None
        )
        target_pace = (
            self._format_pace(round(3600 / target_speed))
            if target_speed is not None
            else None
        )
        threshold_heart_rate = (
            profile.physiological.threshold_heart_rate_bpm
            or profile.physiological.sv2.heart_rate_bpm
        )
        heart_rate_min = (
            round(threshold_heart_rate * 0.90)
            if threshold_heart_rate is not None
            else None
        )
        heart_rate_max = (
            round(threshold_heart_rate * 0.96)
            if threshold_heart_rate is not None
            else None
        )

        workout = AdaptiveWorkout(
            workout_id=self._workout_id(
                workout_date,
                WorkoutType.TEMPO_Z3,
            ),
            workout_date=workout_date,
            workout_type=WorkoutType.TEMPO_Z3,
            title="Rappel allure spécifique semi",
            objective=(
                "Entretenir le rythme de compétition sans créer "
                "de fatigue résiduelle."
            ),
            blocks=[
                TrainingBlock(
                    name="Échauffement progressif",
                    block_type=BlockType.WARM_UP,
                    duration_minutes=15,
                    target=IntensityTarget(
                        zone=2,
                        rpe_0_10=3,
                    ),
                ),
                TrainingBlock(
                    name="Rappels à l'allure objectif",
                    block_type=BlockType.WORK,
                    repetitions=3,
                    duration_minutes=5,
                    recovery_minutes=2,
                    target=IntensityTarget(
                        zone=3,
                        pace_min_per_km=target_pace,
                        pace_max_per_km=target_pace,
                        speed_min_kmh=target_speed,
                        speed_max_kmh=target_speed,
                        heart_rate_min_bpm=heart_rate_min,
                        heart_rate_max_bpm=heart_rate_max,
                        rpe_0_10=6,
                    ),
                    instructions=(
                        "Rester relâché et interrompre le rappel "
                        "si l'effort dépasse la cible."
                    ),
                ),
                TrainingBlock(
                    name="Retour au calme",
                    block_type=BlockType.COOL_DOWN,
                    duration_minutes=10,
                    target=IntensityTarget(
                        zone=1,
                        rpe_0_10=2,
                    ),
                ),
            ],
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=44,
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=48,
                biomechanical_load_0_100=38,
                recovery_min_hours=24,
                recovery_max_hours=36,
            ),
            movable=True,
            maximum_shift_days=1,
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
            ],
            coach_notes=[
                (
                    "Rappel placé selon les préparations de "
                    "compétition historiquement réussies."
                ),
                "Réévaluation Wellness obligatoire le jour même.",
            ],
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