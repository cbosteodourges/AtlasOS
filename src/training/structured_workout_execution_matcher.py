"""Guards Atlas workout matching against false structured-session matches.

A same-day activity with the right sport and a similar duration is not enough
proof that an interval workout was executed. Health Connect often supplies the
sport correctly while laps/segments are absent; in that case Atlas may still
reconstruct intervals from speed/HR streams, but it must find real structural
evidence before confirming the planned workout.
"""

from __future__ import annotations

from .session_models import BlockType
from .workout_execution_matcher import (
    AtlasWorkoutExecutionMatch,
    AtlasWorkoutExecutionMatcher as BaseAtlasWorkoutExecutionMatcher,
)


class AtlasWorkoutExecutionMatcher(BaseAtlasWorkoutExecutionMatcher):
    """Matcher with a structural-evidence gate for repeated work blocks."""

    STRUCTURE_MIN_RATIO = 0.5

    def match(self, planned_workout, activity, analysis) -> AtlasWorkoutExecutionMatch:
        result = super().match(planned_workout, activity, analysis)

        work_blocks = [
            block for block in planned_workout.blocks
            if block.block_type == BlockType.WORK
        ]
        planned_repetitions = sum(
            max(1, int(block.repetitions or 1)) for block in work_blocks
        )

        # Continuous/easy sessions keep the historical matcher behaviour.
        if planned_repetitions <= 1:
            return result

        interval_details = list(result.execution.interval_details or [])
        reconstructed_repetitions = len(interval_details)

        structured = analysis.workout_execution
        device_repetitions = 0
        if activity.workout_steps and structured.planned_repetition_count > 0:
            device_repetitions = int(structured.completed_repetition_count or 0)

        observed_repetitions = max(reconstructed_repetitions, device_repetitions)
        minimum_required = max(2, round(planned_repetitions * self.STRUCTURE_MIN_RATIO))

        if observed_repetitions >= minimum_required:
            return result

        result.matched = False
        reason = (
            "Structure spécifique insuffisante : "
            f"{observed_repetitions}/{planned_repetitions} répétition(s) "
            "identifiée(s). L'activité reste une séance libre analysée et "
            "ne valide pas automatiquement la séance planifiée."
        )
        result.reasons.append(reason)
        result.execution.origin_reasons.append(reason)
        result.execution.observations.append(reason)
        result.score_audit["structure_identity"] = {
            "planned_repetitions": planned_repetitions,
            "observed_repetitions": observed_repetitions,
            "minimum_required": minimum_required,
            "matched": False,
            "method": "preuve structurelle obligatoire pour une séance répétée",
        }
        return result
