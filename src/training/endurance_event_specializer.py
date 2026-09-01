"""Spécialisation des préparations marathon et trail longue distance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from src.performance.athlete_profile import AthleteProfile
from src.performance.models import PerformanceGoal

from .program_models import TrainingPhase
from .session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    IntensityTarget,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class EnduranceEventKind(str, Enum):
    ROAD = "road"
    MARATHON = "marathon"
    TRAIL_20 = "trail_20"
    TRAIL_50 = "trail_50"
    TRAIL_70 = "trail_70"
    TRAIL_100 = "trail_100"


@dataclass(frozen=True, slots=True)
class EnduranceEventSpecification:
    kind: EnduranceEventKind
    label: str
    minimum_preparation_weeks: int
    minimum_weekly_base_km: float
    long_run_ceiling_base: int
    long_run_ceiling_development: int
    long_run_ceiling_specific: int
    back_to_back: bool = False
    fueling_grams_per_hour: tuple[int, int] = (40, 60)

    @property
    def is_trail(self) -> bool:
        return self.kind.value.startswith("trail_")


class EnduranceEventSpecializer:
    """Résout et construit les exigences propres à chaque format."""

    SPECS = {
        EnduranceEventKind.MARATHON: EnduranceEventSpecification(
            EnduranceEventKind.MARATHON,
            "Marathon route",
            12,
            20,
            110,
            150,
            180,
            fueling_grams_per_hour=(50, 80),
        ),
        EnduranceEventKind.TRAIL_20: EnduranceEventSpecification(
            EnduranceEventKind.TRAIL_20,
            "Trail court 20 km",
            8,
            15,
            100,
            130,
            155,
            fueling_grams_per_hour=(40, 60),
        ),
        EnduranceEventKind.TRAIL_50: EnduranceEventSpecification(
            EnduranceEventKind.TRAIL_50,
            "Trail long 50 km",
            12,
            25,
            130,
            190,
            240,
            back_to_back=True,
            fueling_grams_per_hour=(50, 80),
        ),
        EnduranceEventKind.TRAIL_70: EnduranceEventSpecification(
            EnduranceEventKind.TRAIL_70,
            "Ultra-trail 70 km",
            16,
            35,
            150,
            230,
            300,
            back_to_back=True,
            fueling_grams_per_hour=(60, 90),
        ),
        EnduranceEventKind.TRAIL_100: EnduranceEventSpecification(
            EnduranceEventKind.TRAIL_100,
            "Ultra-trail 100 km",
            20,
            45,
            180,
            280,
            360,
            back_to_back=True,
            fueling_grams_per_hour=(60, 90),
        ),
    }

    def resolve(
        self,
        goal: PerformanceGoal,
    ) -> EnduranceEventSpecification | None:
        is_trail = (
            goal.discipline in {"trail", "trail_running"}
            or "trail" in goal.name.casefold()
        )
        if is_trail:
            if goal.distance_km <= 30:
                kind = EnduranceEventKind.TRAIL_20
            elif goal.distance_km <= 60:
                kind = EnduranceEventKind.TRAIL_50
            elif goal.distance_km <= 85:
                kind = EnduranceEventKind.TRAIL_70
            elif goal.distance_km <= 120:
                kind = EnduranceEventKind.TRAIL_100
            else:
                raise ValueError(
                    "Les trails de plus de 120 km ne sont pas encore pris en charge."
                )
            return self.SPECS[kind]

        if 40 <= goal.distance_km <= 45:
            return self.SPECS[EnduranceEventKind.MARATHON]
        return None

    def validate_goal(
        self,
        *,
        goal: PerformanceGoal,
        profile: AthleteProfile,
        preparation_weeks: int,
    ) -> EnduranceEventSpecification | None:
        spec = self.resolve(goal)
        if spec is None:
            return None

        if preparation_weeks < spec.minimum_preparation_weeks:
            raise ValueError(
                f"{spec.label} exige au moins "
                f"{spec.minimum_preparation_weeks} semaines de préparation."
            )
        if spec.is_trail:
            if goal.elevation_gain_m is None or goal.elevation_gain_m <= 0:
                raise ValueError(
                    "Un objectif trail doit préciser le dénivelé positif."
                )
            if goal.terrain_technicality not in {
                "low",
                "moderate",
                "high",
                "very_high",
            }:
                raise ValueError(
                    "La technicité du trail doit être low, moderate, "
                    "high ou very_high."
                )

        weekly_base = (
            profile.tolerance.usual_running_distance_per_week_km
            or 0
        )
        maximum_base = (
            profile.tolerance.maximum_tolerated_weekly_distance_km
            or weekly_base
        )
        known_base = max(weekly_base, maximum_base)
        if known_base < spec.minimum_weekly_base_km:
            raise ValueError(
                f"{spec.label} nécessite une base documentée d'au moins "
                f"{spec.minimum_weekly_base_km:g} km par semaine ; "
                f"profil actuel : {known_base:g} km."
            )
        return spec

    def long_run_duration(
        self,
        *,
        spec: EnduranceEventSpecification,
        phase: TrainingPhase,
        week_number: int,
        progression_percent: float,
    ) -> int:
        ceiling = {
            TrainingPhase.BASE: spec.long_run_ceiling_base,
            TrainingPhase.DEVELOPMENT: (
                spec.long_run_ceiling_development
            ),
            TrainingPhase.SPECIFIC: (
                spec.long_run_ceiling_specific
            ),
        }.get(phase, spec.long_run_ceiling_base)
        start = 75 if spec.kind == EnduranceEventKind.MARATHON else 90
        progressive = round(
            start
            * ((1 + progression_percent / 100) ** max(0, week_number - 1))
        )
        return min(ceiling, progressive)

    def specialize_long_run(
        self,
        workout: AdaptiveWorkout,
        *,
        goal: PerformanceGoal,
        spec: EnduranceEventSpecification,
        phase: TrainingPhase,
    ) -> AdaptiveWorkout:
        low, high = spec.fueling_grams_per_hour
        workout.title = f"Sortie longue spécifique · {spec.label}"
        workout.fueling_strategy = (
            f"Tester {low} à {high} g de glucides par heure, "
            "avec hydratation et sodium individualisés."
        )
        workout.coach_notes.extend([
            workout.fueling_strategy,
            "Aucun nouveau produit ni matériel le jour de la compétition.",
        ])

        main = next(
            (
                block
                for block in workout.blocks
                if block.block_type == BlockType.CONTINUOUS
            ),
            None,
        )
        if main is not None:
            main.instructions = (
                main.instructions
                + " "
                + workout.fueling_strategy
            )

        if spec.kind == EnduranceEventKind.MARATHON:
            workout.objective = (
                "Développer l'endurance marathon, la résistance musculaire "
                "et la stratégie énergétique."
            )
            workout.terrain_focus = "route et allure régulière"
            return workout

        workout.objective = (
            "Développer le temps d'effort, la marche active en montée, "
            "la résistance excentrique en descente et l'autonomie."
        )
        workout.terrain_focus = (
            f"trail {goal.terrain_technicality}, montées et descentes"
        )
        race_gain = goal.elevation_gain_m or 0
        phase_fraction = {
            TrainingPhase.BASE: 0.12,
            TrainingPhase.DEVELOPMENT: 0.20,
            TrainingPhase.SPECIFIC: 0.30,
        }.get(phase, 0.12)
        distance_factor = {
            EnduranceEventKind.TRAIL_20: 1.0,
            EnduranceEventKind.TRAIL_50: 0.9,
            EnduranceEventKind.TRAIL_70: 0.8,
            EnduranceEventKind.TRAIL_100: 0.7,
        }[spec.kind]
        workout.planned_elevation_gain_m = max(
            100,
            round(race_gain * phase_fraction * distance_factor),
        )
        workout.planned_elevation_loss_m = (
            workout.planned_elevation_gain_m
        )
        if main is not None:
            main.target.gradient_min_percent = 3
            main.target.gradient_max_percent = (
                12 if goal.terrain_technicality in {"low", "moderate"} else 20
            )
            main.instructions += (
                " Alterner course et marche active selon la pente ; "
                "descendre relâché sans rechercher la vitesse."
            )
        return workout

    def build_specific_quality(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        spec: EnduranceEventSpecification,
        workout_date: date,
        phase: TrainingPhase,
    ) -> AdaptiveWorkout:
        if spec.kind == EnduranceEventKind.MARATHON:
            return self._build_marathon_quality(
                profile=profile,
                goal=goal,
                workout_date=workout_date,
                phase=phase,
            )
        return self._build_trail_quality(
            profile=profile,
            goal=goal,
            spec=spec,
            workout_date=workout_date,
            phase=phase,
        )

    def _build_marathon_quality(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        workout_date: date,
        phase: TrainingPhase,
    ) -> AdaptiveWorkout:
        repetitions, duration = {
            TrainingPhase.BASE: (3, 8),
            TrainingPhase.DEVELOPMENT: (3, 12),
            TrainingPhase.SPECIFIC: (3, 18),
        }.get(phase, (3, 8))
        target_speed = (
            goal.distance_km / (goal.target_time_minutes / 60)
            if goal.target_time_minutes
            else (
                (profile.physiological.threshold_speed_kmh or 12.0) * 0.84
            )
        )
        target_speed = round(target_speed, 2)
        blocks = self._framed_blocks(
            TrainingBlock(
                name="Blocs à allure marathon",
                block_type=BlockType.WORK,
                repetitions=repetitions,
                duration_minutes=duration,
                recovery_minutes=3,
                target=IntensityTarget(
                    zone=3,
                    speed_min_kmh=round(target_speed * 0.98, 2),
                    speed_max_kmh=round(target_speed * 1.02, 2),
                    rpe_0_10=6,
                ),
                instructions=(
                    "Allure régulière, relâchée et compatible avec "
                    "la stratégie énergétique de course."
                ),
            )
        )
        return self._workout(
            workout_date=workout_date,
            workout_type=WorkoutType.RACE_SPECIFIC,
            title=(
                f"Allure marathon · {repetitions} × {duration} min"
            ),
            objective=(
                "Stabiliser l'économie de course à l'allure marathon."
            ),
            blocks=blocks,
            terrain_focus="route régulière",
            fueling_strategy=(
                "Tester la boisson et les glucides prévus en compétition."
            ),
        )

    def _build_trail_quality(
        self,
        *,
        profile: AthleteProfile,
        goal: PerformanceGoal,
        spec: EnduranceEventSpecification,
        workout_date: date,
        phase: TrainingPhase,
    ) -> AdaptiveWorkout:
        repetitions, duration = {
            EnduranceEventKind.TRAIL_20: (6, 3),
            EnduranceEventKind.TRAIL_50: (5, 6),
            EnduranceEventKind.TRAIL_70: (4, 10),
            EnduranceEventKind.TRAIL_100: (3, 15),
        }[spec.kind]
        if phase == TrainingPhase.BASE:
            duration = max(2, round(duration * 0.65))
        elif phase == TrainingPhase.DEVELOPMENT:
            duration = max(3, round(duration * 0.82))

        work = TrainingBlock(
            name="Montée en course ou marche active",
            block_type=BlockType.WORK,
            repetitions=repetitions,
            duration_minutes=duration,
            recovery_minutes=max(2, round(duration * 0.35)),
            target=IntensityTarget(
                zone=3,
                rpe_0_10=6.5,
                gradient_min_percent=5,
                gradient_max_percent=20,
            ),
            instructions=(
                "Monter économiquement ; récupération en descente "
                "contrôlée avec cadence courte et appuis stables."
            ),
        )
        workout = self._workout(
            workout_date=workout_date,
            workout_type=WorkoutType.HILL_SPRINTS,
            title=(
                f"Côtes spécifiques {spec.label} · "
                f"{repetitions} × {duration} min"
            ),
            objective=(
                "Développer l'efficacité en montée et la tolérance "
                "excentrique en descente."
            ),
            blocks=self._framed_blocks(work),
            terrain_focus=(
                f"trail {goal.terrain_technicality}, montée et descente"
            ),
            fueling_strategy="Tester l'hydratation si la séance dépasse 75 min.",
        )
        race_gain = goal.elevation_gain_m or 0
        workout.planned_elevation_gain_m = max(
            150,
            round(race_gain * 0.12),
        )
        workout.planned_elevation_loss_m = workout.planned_elevation_gain_m
        return workout

    @staticmethod
    def _framed_blocks(work: TrainingBlock) -> list[TrainingBlock]:
        return [
            TrainingBlock(
                name="Échauffement progressif",
                block_type=BlockType.WARM_UP,
                duration_minutes=15,
                target=IntensityTarget(zone=2, rpe_0_10=3),
            ),
            work,
            TrainingBlock(
                name="Retour au calme",
                block_type=BlockType.COOL_DOWN,
                duration_minutes=10,
                target=IntensityTarget(zone=1, rpe_0_10=2),
            ),
        ]

    @staticmethod
    def _workout(
        *,
        workout_date: date,
        workout_type: WorkoutType,
        title: str,
        objective: str,
        blocks: list[TrainingBlock],
        terrain_focus: str,
        fueling_strategy: str,
    ) -> AdaptiveWorkout:
        workout = AdaptiveWorkout(
            workout_id=(
                f"{workout_date.isoformat()}-"
                f"{workout_type.value}-endurance-specific"
            ),
            workout_date=workout_date,
            workout_type=workout_type,
            title=title,
            objective=objective,
            blocks=blocks,
            priority=WorkoutPriority.KEY,
            planned_duration_minutes=round(
                sum(block.estimated_duration_minutes for block in blocks)
            ),
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=82,
                biomechanical_load_0_100=78,
                recovery_min_hours=36,
                recovery_max_hours=72,
                sensitive_structures=[
                    "pieds",
                    "mollets",
                    "tendons d'Achille",
                    "genoux",
                    "quadriceps",
                ],
            ),
            maximum_shift_days=1,
            replacement_types=[WorkoutType.ENDURANCE_Z2],
            terrain_focus=terrain_focus,
            fueling_strategy=fueling_strategy,
            coach_notes=[
                fueling_strategy,
                "Réévaluation récupération et douleur le jour même.",
            ],
        )
        workout.validate()
        return workout
