"""
ATLAS OS
Analyse de la réponse réelle à 24–72 heures.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

from .session_models import AdaptiveWorkout


class TrainingResponseOutcome(str, Enum):
    """Classification de la réponse à une séance."""

    POSITIVE = "positive"
    EXPECTED = "expected"
    DELAYED = "delayed"
    ADVERSE = "adverse"
    INSUFFICIENT = "insufficient"


@dataclass(slots=True)
class TrainingResponseObservation:
    """Observation réalisée entre 24 et 72 heures."""

    workout_id: str
    hours_after_session: int

    recovery_score: Optional[float] = None
    atlas_index_score: Optional[float] = None
    hrv_ms: Optional[float] = None
    resting_heart_rate_bpm: Optional[float] = None
    sleep_score: Optional[float] = None

    fatigue_0_10: Optional[float] = None
    muscle_soreness_0_10: Optional[float] = None
    pain_0_10: Optional[float] = None
    illness_symptoms: bool = False

    workout_completed: bool = True
    actual_rpe_0_10: Optional[float] = None
    notes: str = ""

    def validate(self) -> None:
        if not self.workout_id.strip():
            raise ValueError("workout_id est obligatoire.")
        if not 24 <= self.hours_after_session <= 72:
            raise ValueError(
                "hours_after_session doit être compris "
                "entre 24 et 72 heures."
            )

        for name in (
            "fatigue_0_10",
            "muscle_soreness_0_10",
            "pain_0_10",
            "actual_rpe_0_10",
        ):
            value = getattr(self, name)
            if value is not None and not 0 <= value <= 10:
                raise ValueError(
                    f"{name} doit être compris entre 0 et 10."
                )

        for name in (
            "recovery_score",
            "atlas_index_score",
            "sleep_score",
        ):
            value = getattr(self, name)
            if value is not None and not 0 <= value <= 100:
                raise ValueError(
                    f"{name} doit être compris entre 0 et 100."
                )


@dataclass(slots=True)
class TrainingResponseLearning:
    """Résultat transmis au profil adaptatif de l’athlète."""

    workout_id: str
    outcome: TrainingResponseOutcome
    confidence_score: int
    next_load_factor: float

    physiological_tolerance_delta: int
    biomechanical_tolerance_delta: int
    usable_for_learning: bool

    observations_count: int
    latest_checkpoint_hours: Optional[int]
    reasons: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["outcome"] = self.outcome.value
        return result


class TrainingResponseLearningEngine:
    """Compare la réponse observée à la réponse attendue."""

    def analyze(
        self,
        workout: AdaptiveWorkout,
        observations: list[TrainingResponseObservation],
        *,
        pre_session_recovery_score: Optional[float] = None,
        pre_session_atlas_index_score: Optional[float] = None,
        pre_session_pain_0_10: Optional[float] = None,
    ) -> TrainingResponseLearning:
        """Analyse les observations disponibles à 24–72 heures."""
        workout.validate()

        if not observations:
            return self._result(
                workout,
                TrainingResponseOutcome.INSUFFICIENT,
                confidence=0,
                observations_count=0,
                latest_checkpoint=None,
                reasons=[
                    "Aucune réponse à 24–72 heures disponible."
                ],
            )

        ordered = sorted(
            observations,
            key=lambda item: item.hours_after_session,
        )

        for observation in ordered:
            observation.validate()
            if observation.workout_id != workout.workout_id:
                raise ValueError(
                    "Une observation ne correspond pas "
                    "à la séance analysée."
                )

        latest = ordered[-1]
        confidence = self._confidence(ordered)
        recovery_delta = self._difference(
            latest.recovery_score,
            pre_session_recovery_score,
        )
        atlas_delta = self._difference(
            latest.atlas_index_score,
            pre_session_atlas_index_score,
        )
        pain_delta = self._difference(
            latest.pain_0_10,
            pre_session_pain_0_10,
        )

        reasons = [
            (
                f"{len(ordered)} observation(s), dernière "
                f"à {latest.hours_after_session} heures."
            )
        ]
        alerts: list[str] = []

        if recovery_delta is not None:
            reasons.append(
                f"Évolution de la récupération : "
                f"{recovery_delta:+.1f} point(s)."
            )
        if atlas_delta is not None:
            reasons.append(
                f"Évolution de l’Indice ATLAS : "
                f"{atlas_delta:+.1f} point(s)."
            )
        if pain_delta is not None:
            reasons.append(
                f"Évolution de la douleur : "
                f"{pain_delta:+.1f} point(s)."
            )

        maximum_pain = self._maximum(
            item.pain_0_10 for item in ordered
        )
        maximum_fatigue = self._maximum(
            item.fatigue_0_10 for item in ordered
        )
        maximum_soreness = self._maximum(
            item.muscle_soreness_0_10
            for item in ordered
        )
        illness = any(
            item.illness_symptoms for item in ordered
        )

        if illness:
            alerts.append(
                "Symptômes de maladie signalés après la séance."
            )
        if maximum_pain is not None and maximum_pain >= 7:
            alerts.append(
                "Douleur importante signalée après la séance."
            )
        if pain_delta is not None and pain_delta >= 3:
            alerts.append(
                "Augmentation marquée de la douleur."
            )

        if alerts:
            return self._result(
                workout,
                TrainingResponseOutcome.ADVERSE,
                confidence=confidence,
                observations_count=len(ordered),
                latest_checkpoint=latest.hours_after_session,
                reasons=reasons + [
                    "La réponse dépasse les limites de "
                    "tolérance acceptables."
                ],
                alerts=alerts,
            )

        expected_max_hours = (
            workout.expected_response.recovery_max_hours
            if workout.expected_response is not None
            else 48
        )
        recovery_window_reached = (
            latest.hours_after_session
            >= min(72, expected_max_hours)
        )

        delayed_signals = [
            recovery_delta is not None
            and recovery_delta <= -10,
            maximum_fatigue is not None
            and maximum_fatigue >= 7,
            maximum_soreness is not None
            and maximum_soreness >= 7,
            pain_delta is not None
            and pain_delta >= 2,
        ]

        if recovery_window_reached and any(delayed_signals):
            return self._result(
                workout,
                TrainingResponseOutcome.DELAYED,
                confidence=confidence,
                observations_count=len(ordered),
                latest_checkpoint=latest.hours_after_session,
                reasons=reasons + [
                    "La récupération reste incomplète à la fin "
                    "de la fenêtre attendue."
                ],
            )

        expected_min_hours = (
            workout.expected_response.recovery_min_hours
            if workout.expected_response is not None
            else 24
        )
        minimum_window_reached = (
            latest.hours_after_session >= expected_min_hours
        )

        favorable = all([
            minimum_window_reached,
            latest.workout_completed,
            recovery_delta is None or recovery_delta >= 0,
            pain_delta is None or pain_delta <= 0,
            latest.fatigue_0_10 is None
            or latest.fatigue_0_10 <= 3,
            latest.muscle_soreness_0_10 is None
            or latest.muscle_soreness_0_10 <= 3,
            latest.actual_rpe_0_10 is None
            or latest.actual_rpe_0_10 <= 8,
        ])

        if favorable:
            return self._result(
                workout,
                TrainingResponseOutcome.POSITIVE,
                confidence=confidence,
                observations_count=len(ordered),
                latest_checkpoint=latest.hours_after_session,
                reasons=reasons + [
                    "La séance est bien tolérée et la "
                    "récupération est au moins conforme."
                ],
            )

        if not recovery_window_reached and confidence < 60:
            return self._result(
                workout,
                TrainingResponseOutcome.INSUFFICIENT,
                confidence=confidence,
                observations_count=len(ordered),
                latest_checkpoint=latest.hours_after_session,
                reasons=reasons + [
                    "La fenêtre d’observation est encore "
                    "trop courte pour conclure."
                ],
            )

        return self._result(
            workout,
            TrainingResponseOutcome.EXPECTED,
            confidence=confidence,
            observations_count=len(ordered),
            latest_checkpoint=latest.hours_after_session,
            reasons=reasons + [
                "La réponse reste dans la plage attendue."
            ],
        )

    @staticmethod
    def _confidence(
        observations: list[TrainingResponseObservation],
    ) -> int:
        checkpoint_score = min(
            60,
            len({
                item.hours_after_session
                for item in observations
            }) * 20,
        )
        latest = observations[-1]
        available_metrics = sum(
            value is not None
            for value in (
                latest.recovery_score,
                latest.atlas_index_score,
                latest.hrv_ms,
                latest.resting_heart_rate_bpm,
                latest.sleep_score,
                latest.fatigue_0_10,
                latest.muscle_soreness_0_10,
                latest.pain_0_10,
                latest.actual_rpe_0_10,
            )
        )
        metric_score = min(40, available_metrics * 5)
        return min(100, checkpoint_score + metric_score)

    @staticmethod
    def _difference(
        current: Optional[float],
        baseline: Optional[float],
    ) -> Optional[float]:
        if current is None or baseline is None:
            return None
        return round(float(current) - float(baseline), 1)

    @staticmethod
    def _maximum(
        values,
    ) -> Optional[float]:
        available = [
            float(value)
            for value in values
            if value is not None
        ]
        return max(available) if available else None

    @staticmethod
    def _result(
        workout: AdaptiveWorkout,
        outcome: TrainingResponseOutcome,
        *,
        confidence: int,
        observations_count: int,
        latest_checkpoint: Optional[int],
        reasons: list[str],
        alerts: Optional[list[str]] = None,
    ) -> TrainingResponseLearning:
        settings = {
            TrainingResponseOutcome.POSITIVE: (
                1.05, 2, 2
            ),
            TrainingResponseOutcome.EXPECTED: (
                1.00, 0, 0
            ),
            TrainingResponseOutcome.DELAYED: (
                0.85, -5, -4
            ),
            TrainingResponseOutcome.ADVERSE: (
                0.65, -10, -12
            ),
            TrainingResponseOutcome.INSUFFICIENT: (
                1.00, 0, 0
            ),
        }
        load_factor, physiological_delta, mechanical_delta = (
            settings[outcome]
        )

        return TrainingResponseLearning(
            workout_id=workout.workout_id,
            outcome=outcome,
            confidence_score=confidence,
            next_load_factor=load_factor,
            physiological_tolerance_delta=(
                physiological_delta
            ),
            biomechanical_tolerance_delta=(
                mechanical_delta
            ),
            usable_for_learning=(
                confidence >= 60
                and outcome
                != TrainingResponseOutcome.INSUFFICIENT
            ),
            observations_count=observations_count,
            latest_checkpoint_hours=latest_checkpoint,
            reasons=reasons,
            alerts=alerts or [],
        )