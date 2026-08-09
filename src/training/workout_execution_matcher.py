"""
ATLAS OS
Rapproche une séance planifiée Atlas et une activité réellement exécutée.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from src.performance import (
    DetailedSessionAnalysis,
    LongitudinalActivity,
    WorkoutExecutionSummary,
)

from .session_models import AdaptiveWorkout, TrainingBlock


@dataclass(slots=True)
class AtlasWorkoutExecutionMatch:
    """Résultat du rapprochement entre le calendrier et le FIT."""

    workout_id: str
    activity_id: str
    matched: bool
    match_confidence_score: int
    execution: WorkoutExecutionSummary
    date_difference_days: int = 0
    duration_compliance_score: Optional[int] = None
    distance_compliance_score: Optional[int] = None
    target_compliance_score: Optional[int] = None
    physiological_load_score: int = 0
    biomechanical_load_score: int = 0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Convertit le résultat en dictionnaire sérialisable."""
        result = asdict(self)
        return result


class AtlasWorkoutExecutionMatcher:
    """Compare une activité réelle à une séance Atlas planifiée."""

    MATCH_THRESHOLD = 70

    def match(
        self,
        planned_workout: AdaptiveWorkout,
        activity: LongitudinalActivity,
        analysis: DetailedSessionAnalysis,
    ) -> AtlasWorkoutExecutionMatch:
        """Rapproche une activité et une séance du calendrier."""
        planned_workout.validate()

        date_difference = abs(
            (
                activity.start_time.date()
                - planned_workout.workout_date
            ).days
        )

        date_score = self._date_score(date_difference)
        sport_score = self._sport_score(
            planned_workout.sport,
            activity.activity_type,
        )
        duration_score = self._ratio_score(
            activity.duration_minutes,
            planned_workout.estimated_duration_minutes,
        )
        distance_score = self._optional_ratio_score(
            activity.distance_km,
            planned_workout.planned_distance_km,
        )
        target_score = self._target_compliance(
            planned_workout.blocks,
            analysis,
        )

        matching_scores = [
            (date_score, 50),
            (sport_score, 20),
            (duration_score, 15),
        ]
        if distance_score is not None:
            matching_scores.append((distance_score, 15))

        match_confidence = self._weighted_score(
            matching_scores
        )
        matched = (
            match_confidence >= self.MATCH_THRESHOLD
        )

        execution_scores = [
            (duration_score, 30),
            (target_score, 40),
        ]
        if distance_score is not None:
            execution_scores.append((distance_score, 30))

        execution_score = self._weighted_score(
            execution_scores
        )

        planned_repetitions = sum(
            block.repetitions
            for block in planned_workout.blocks
        )
        executed_active_blocks = [
            block
            for block in analysis.blocks
            if block.block_type
            not in {"recovery", "warm_up", "cool_down"}
        ]

        reasons = [
            (
                f"Écart de date : "
                f"{date_difference} jour(s)."
            ),
            (
                f"Compatibilité du sport : "
                f"{sport_score}/100."
            ),
            (
                f"Respect de la durée : "
                f"{duration_score}/100."
            ),
            (
                f"Respect des cibles : "
                f"{target_score}/100."
            ),
        ]

        if distance_score is not None:
            reasons.append(
                f"Respect de la distance : "
                f"{distance_score}/100."
            )

        if not matched:
            reasons.append(
                "Correspondance insuffisante pour "
                "apprendre automatiquement."
            )

        execution = WorkoutExecutionSummary(
            workout_name=planned_workout.title,
            workout_origin="atlas",
            origin_confidence_score=match_confidence,
            origin_reasons=reasons.copy(),
            planned_step_count=len(
                planned_workout.blocks
            ),
            executed_block_count=len(analysis.blocks),
            planned_repetition_count=planned_repetitions,
            completed_repetition_count=min(
                planned_repetitions,
                len(executed_active_blocks),
            ),
            target_compliance_score=target_score,
            execution_score=execution_score,
            observations=reasons.copy(),
        )

        return AtlasWorkoutExecutionMatch(
            workout_id=planned_workout.workout_id,
            activity_id=activity.atlas_id,
            matched=matched,
            match_confidence_score=match_confidence,
            execution=execution,
            date_difference_days=date_difference,
            duration_compliance_score=duration_score,
            distance_compliance_score=distance_score,
            target_compliance_score=target_score,
            physiological_load_score=(
                analysis.physiological_load_score
            ),
            biomechanical_load_score=(
                analysis.biomechanical_load_score
            ),
            reasons=reasons,
        )

    def _target_compliance(
        self,
        planned_blocks: list[TrainingBlock],
        analysis: DetailedSessionAnalysis,
    ) -> int:
        actual_blocks = [
            block
            for block in analysis.blocks
            if block.block_type
            not in {"recovery", "warm_up", "cool_down"}
        ]
        planned_active = [
            block
            for block in planned_blocks
            if block.target.zone is not None
            or block.target.speed_min_kmh is not None
            or block.target.heart_rate_min_bpm is not None
        ]

        if not planned_active or not actual_blocks:
            return 50

        scores = []
        for actual in actual_blocks:
            scores.append(
                max(
                    self._block_target_score(
                        planned,
                        actual,
                    )
                    for planned in planned_active
                )
            )

        return round(sum(scores) / len(scores))

    @staticmethod
    def _block_target_score(
        planned: TrainingBlock,
        actual: object,
    ) -> int:
        scores: list[int] = []
        target = planned.target

        if target.zone is not None:
            expected_type = f"z{target.zone}"
            scores.append(
                100
                if getattr(
                    actual,
                    "block_type",
                    "",
                ) == expected_type
                else 0
            )

        speed = getattr(
            actual,
            "average_speed_kmh",
            None,
        )
        if (
            speed is not None
            and target.speed_min_kmh is not None
            and target.speed_max_kmh is not None
        ):
            scores.append(
                100
                if (
                    target.speed_min_kmh
                    <= speed
                    <= target.speed_max_kmh
                )
                else 0
            )

        heart_rate = getattr(
            actual,
            "average_heart_rate_bpm",
            None,
        )
        if (
            heart_rate is not None
            and target.heart_rate_min_bpm is not None
            and target.heart_rate_max_bpm is not None
        ):
            scores.append(
                100
                if (
                    target.heart_rate_min_bpm
                    <= heart_rate
                    <= target.heart_rate_max_bpm
                )
                else 0
            )

        if not scores:
            return 50

        return round(sum(scores) / len(scores))

    @staticmethod
    def _date_score(difference_days: int) -> int:
        if difference_days == 0:
            return 100
        if difference_days == 1:
            return 75
        if difference_days == 2:
            return 45
        return 0

    @staticmethod
    def _sport_score(
        planned_sport: str,
        actual_sport: str,
    ) -> int:
        planned = planned_sport.strip().lower()
        actual = actual_sport.strip().lower()

        running_aliases = {
            "running",
            "run",
            "course",
            "course à pied",
        }

        if planned == actual:
            return 100
        if (
            planned in running_aliases
            and actual in running_aliases
        ):
            return 100
        return 0

    @classmethod
    def _optional_ratio_score(
        cls,
        actual: Optional[float],
        planned: Optional[float],
    ) -> Optional[int]:
        if (
            actual is None
            or planned is None
            or planned <= 0
        ):
            return None
        return cls._ratio_score(actual, planned)

    @staticmethod
    def _ratio_score(
        actual: float,
        planned: float,
    ) -> int:
        if planned <= 0:
            return 0

        difference_ratio = abs(actual - planned) / planned
        return max(
            0,
            min(
                100,
                round(100 - difference_ratio * 100),
            ),
        )

    @staticmethod
    def _weighted_score(
        values: list[tuple[int, int]],
    ) -> int:
        total_weight = sum(weight for _, weight in values)
        if total_weight <= 0:
            return 0

        return round(
            sum(
                score * weight
                for score, weight in values
            )
            / total_weight
        )