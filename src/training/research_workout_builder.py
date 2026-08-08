"""Transformation d’un protocole Atlas Research en séance Coach."""

from __future__ import annotations

from datetime import date

from src.performance.athlete_profile import AthleteProfile
from src.research.training_protocol import (
    ProtocolBlockDefinition,
)
from src.research.training_protocol_selector import (
    ProtocolSelection,
)

from .session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    IntensityTarget,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class ResearchWorkoutBuilder:
    """Convertit une sélection scientifique en séance personnalisée."""

    def build(
        self,
        *,
        selection: ProtocolSelection,
        profile: AthleteProfile,
        workout_date: date,
        workout_id: str | None = None,
    ) -> AdaptiveWorkout:
        """Construit une séance exploitable par la boucle adaptative."""
        protocol = selection.protocol
        workout_type = WorkoutType(protocol.workout_type_key)

        blocks = [
            self._warm_up_block(),
            *[
                self._research_block(block, profile)
                for block in protocol.blocks
            ],
            self._cool_down_block(),
        ]
        coach_notes = [
            (
                "Protocole Atlas Research : "
                f"{protocol.protocol_id} v{protocol.version}."
            ),
            (
                "Adéquation individuelle estimée : "
                f"{selection.suitability_score}/100."
            ),
            (
                "Confiance scientifique : "
                f"{selection.evidence_score}/100."
            ),
            *selection.warnings,
        ]

        workout = AdaptiveWorkout(
            workout_id=(
                workout_id
                or (
                    f"{workout_date.isoformat()}-"
                    f"{protocol.workout_type_key}"
                )
            ),
            workout_date=workout_date,
            workout_type=workout_type,
            title=protocol.title,
            objective=" ; ".join(protocol.objectives),
            blocks=blocks,
            priority=WorkoutPriority.KEY,
            expected_response=self._expected_response(
                workout_type
            ),
            replacement_types=[
                WorkoutType.ENDURANCE_Z2,
                WorkoutType.RECOVERY_RUN,
            ],
            coach_notes=coach_notes,
        )
        workout.validate()
        return workout

    @staticmethod
    def _warm_up_block() -> TrainingBlock:
        return TrainingBlock(
            name="Échauffement progressif",
            block_type=BlockType.WARM_UP,
            duration_minutes=15,
            target=IntensityTarget(
                zone=2,
                rpe_0_10=3,
            ),
            instructions=(
                "Course facile, mobilité dynamique puis quelques "
                "accélérations progressives adaptées à la séance."
            ),
        )

    @staticmethod
    def _cool_down_block() -> TrainingBlock:
        return TrainingBlock(
            name="Retour au calme",
            block_type=BlockType.COOL_DOWN,
            duration_minutes=10,
            target=IntensityTarget(
                zone=1,
                rpe_0_10=2,
            ),
            instructions=(
                "Revenir progressivement à une allure très facile."
            ),
        )

    def _research_block(
        self,
        block: ProtocolBlockDefinition,
        profile: AthleteProfile,
    ) -> TrainingBlock:
        return TrainingBlock(
            name=block.name,
            block_type=BlockType.WORK,
            repetitions=block.repetitions,
            duration_minutes=(
                None
                if block.duration_seconds is None
                else block.duration_seconds / 60
            ),
            distance_meters=block.distance_meters,
            recovery_minutes=(
                None
                if block.recovery_seconds is None
                else block.recovery_seconds / 60
            ),
            target=self._intensity_target(
                block,
                profile,
            ),
            instructions=block.instructions,
        )

    def _intensity_target(
        self,
        block: ProtocolBlockDefinition,
        profile: AthleteProfile,
    ) -> IntensityTarget:
        reference_speed = self._reference_speed(
            block,
            profile,
        )
        speed_min = self._percentage_speed(
            reference_speed,
            block.intensity_min_percent,
        )
        speed_max = self._percentage_speed(
            reference_speed,
            block.intensity_max_percent,
        )

        return IntensityTarget(
            speed_min_kmh=speed_min,
            speed_max_kmh=speed_max,
            rpe_0_10=self._target_rpe(block),
            gradient_min_percent=block.gradient_min_percent,
            gradient_max_percent=block.gradient_max_percent,
            intensity_pattern=block.intensity_pattern.value,
        )

    @staticmethod
    def _reference_speed(
        block: ProtocolBlockDefinition,
        profile: AthleteProfile,
    ) -> float | None:
        physiological = profile.physiological

        if block.intensity_basis == "vma":
            return physiological.vma_kmh

        if (
            block.intensity_basis
            == "individual_threshold_speed"
        ):
            return (
                physiological.threshold_speed_kmh
                or physiological.sv2.speed_kmh
            )

        return None

    @staticmethod
    def _percentage_speed(
        reference_speed: float | None,
        percentage: float | None,
    ) -> float | None:
        if reference_speed is None or percentage is None:
            return None

        return round(reference_speed * percentage / 100, 2)

    @staticmethod
    def _target_rpe(
        block: ProtocolBlockDefinition,
    ) -> float:
        if block.intensity_basis == "effort_maximal_controle":
            return 9.5

        maximum = block.intensity_max_percent or 0

        if maximum >= 100:
            return 9.0
        if maximum >= 95:
            return 8.0
        return 7.0

    @staticmethod
    def _expected_response(
        workout_type: WorkoutType,
    ) -> ExpectedTrainingResponse:
        responses = {
            WorkoutType.HILL_SPRINTS: (
                75,
                85,
                ["mollets", "tendons d'Achille", "ischio-jambiers"],
            ),
            WorkoutType.MIXED_THRESHOLD_VO2: (
                90,
                70,
                ["mollets", "tendons d'Achille"],
            ),
            WorkoutType.TRIANGULAR_VO2: (
                88,
                68,
                ["mollets", "tendons d'Achille"],
            ),
        }
        physiological, biomechanical, structures = responses[
            workout_type
        ]

        return ExpectedTrainingResponse(
            physiological_load_0_100=physiological,
            biomechanical_load_0_100=biomechanical,
            recovery_min_hours=48,
            recovery_max_hours=72,
            sensitive_structures=structures,
        )