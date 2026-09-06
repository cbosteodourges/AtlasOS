"""Guards Atlas workout matching against false planned-session matches.

Health Connect already tells Atlas the sport. Matching a real activity to a
planned workout therefore needs two further kinds of evidence:

* repeated/interval workouts need real structural evidence;
* a workout on another calendar day needs convincing target evidence, so an
  ordinary free run cannot silently consume tomorrow's easy workout.
"""

from __future__ import annotations

from .session_models import BlockType
from .workout_execution_matcher import (
    AtlasWorkoutExecutionMatch,
    AtlasWorkoutExecutionMatcher as BaseAtlasWorkoutExecutionMatcher,
)


class AtlasWorkoutExecutionMatcher(BaseAtlasWorkoutExecutionMatcher):
    """Matcher with identity gates beyond date + sport + duration."""

    STRUCTURE_MIN_RATIO = 0.5
    SHIFTED_TARGET_MIN_SCORE = 70

    def match(self, planned_workout, activity, analysis) -> AtlasWorkoutExecutionMatch:
        result = super().match(planned_workout, activity, analysis)

        work_blocks = [
            block for block in planned_workout.blocks
            if block.block_type == BlockType.WORK
        ]
        planned_repetitions = sum(
            max(1, int(block.repetitions or 1)) for block in work_blocks
        )

        if planned_repetitions > 1:
            interval_details = list(result.execution.interval_details or [])
            reconstructed_repetitions = len(interval_details)

            structured = analysis.workout_execution
            device_repetitions = 0
            if activity.workout_steps and structured.planned_repetition_count > 0:
                device_repetitions = int(structured.completed_repetition_count or 0)

            observed_repetitions = max(reconstructed_repetitions, device_repetitions)
            minimum_required = max(
                2,
                round(planned_repetitions * self.STRUCTURE_MIN_RATIO),
            )

            if observed_repetitions < minimum_required:
                self._reject(
                    result,
                    (
                        "Structure spécifique insuffisante : "
                        f"{observed_repetitions}/{planned_repetitions} répétition(s) "
                        "identifiée(s). L'activité reste une séance libre analysée et "
                        "ne valide pas automatiquement la séance planifiée."
                    ),
                )
                result.score_audit["structure_identity"] = {
                    "planned_repetitions": planned_repetitions,
                    "observed_repetitions": observed_repetitions,
                    "minimum_required": minimum_required,
                    "matched": False,
                    "method": "preuve structurelle obligatoire pour une séance répétée",
                }
                return result

        # A free activity must not consume yesterday's/tomorrow's workout just
        # because its sport and duration look plausible. Cross-day matching is
        # retained for genuinely displaced sessions when the physiological
        # target itself provides strong evidence.
        target_score = result.target_compliance_score
        if (
            result.matched
            and result.date_difference_days > 0
            and (
                target_score is None
                or target_score < self.SHIFTED_TARGET_MIN_SCORE
            )
        ):
            self._reject(
                result,
                (
                    "Séance d'un autre jour non confirmée : le respect des cibles "
                    f"({target_score if target_score is not None else 'indisponible'}/100) "
                    f"est inférieur au seuil de {self.SHIFTED_TARGET_MIN_SCORE}/100. "
                    "L'activité reste libre et la séance planifiée reste disponible."
                ),
            )
            result.score_audit["shifted_workout_identity"] = {
                "date_difference_days": result.date_difference_days,
                "target_score": target_score,
                "minimum_target_score": self.SHIFTED_TARGET_MIN_SCORE,
                "matched": False,
                "method": "preuve de cible renforcée pour une séance déplacée",
            }

        return result

    @staticmethod
    def _reject(result: AtlasWorkoutExecutionMatch, reason: str) -> None:
        result.matched = False
        result.reasons.append(reason)
        result.execution.origin_reasons.append(reason)
        result.execution.observations.append(reason)
