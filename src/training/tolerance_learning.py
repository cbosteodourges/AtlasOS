"""
ATLAS OS
Mémorisation des réponses à l’entraînement dans le profil athlète.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.performance.athlete_profile import AthleteProfile

from .response_learning import (
    TrainingResponseLearning,
    TrainingResponseOutcome,
)
from .session_models import AdaptiveWorkout


@dataclass(slots=True)
class ToleranceLearningApplication:
    """Résultat traçable de la mise à jour du profil."""

    updated_profile: AthleteProfile
    applied: bool
    changes: list[str] = field(default_factory=list)


class AthleteToleranceLearningEngine:
    """Applique progressivement les réponses fiables au profil."""

    def apply(
        self,
        profile: AthleteProfile,
        workout: AdaptiveWorkout,
        learning: TrainingResponseLearning,
        *,
        learned_at: Optional[datetime] = None,
    ) -> ToleranceLearningApplication:
        """Met à jour une copie du profil sans modifier l’original."""
        updated = deepcopy(profile)

        if learning.workout_id != workout.workout_id:
            raise ValueError(
                "L’apprentissage ne correspond pas à la séance."
            )

        if not learning.usable_for_learning:
            return ToleranceLearningApplication(
                updated_profile=updated,
                applied=False,
                changes=[
                    "Réponse conservée mais non appliquée : "
                    "confiance insuffisante."
                ],
            )

        confidence_factor = (
            learning.confidence_score / 100.0
        )
        physiological_delta = round(
            learning.physiological_tolerance_delta
            * confidence_factor,
            1,
        )
        biomechanical_delta = round(
            learning.biomechanical_tolerance_delta
            * confidence_factor,
            1,
        )

        tolerance = updated.tolerance
        old_physiological = (
            tolerance
            .learned_physiological_tolerance_score
        )
        old_biomechanical = (
            tolerance
            .learned_biomechanical_tolerance_score
        )

        tolerance.learned_physiological_tolerance_score = (
            self._clamp(
                old_physiological
                + physiological_delta
            )
        )
        tolerance.learned_biomechanical_tolerance_score = (
            self._clamp(
                old_biomechanical
                + biomechanical_delta
            )
        )

        tolerance.learned_response_count += 1

        if (
            learning.outcome
            == TrainingResponseOutcome.POSITIVE
        ):
            tolerance.positive_response_count += 1
        elif (
            learning.outcome
            == TrainingResponseOutcome.DELAYED
        ):
            tolerance.delayed_response_count += 1
        elif (
            learning.outcome
            == TrainingResponseOutcome.ADVERSE
        ):
            tolerance.adverse_response_count += 1

        session_key = workout.workout_type.value
        session_delta = round(
            (
                physiological_delta
                + biomechanical_delta
            ) / 2.0,
            1,
        )
        current_session_tolerance = (
            tolerance.session_type_tolerance_scores.get(
                session_key,
                (
                    old_physiological
                    + old_biomechanical
                ) / 2.0,
            )
        )
        tolerance.session_type_tolerance_scores[
            session_key
        ] = self._clamp(
            current_session_tolerance
            + session_delta
        )

        sensitive_structures = (
            workout.expected_response.sensitive_structures
            if workout.expected_response is not None
            else []
        )

        for structure in sensitive_structures:
            current_structure_tolerance = (
                tolerance.structure_tolerance_scores.get(
                    structure,
                    old_biomechanical,
                )
            )
            tolerance.structure_tolerance_scores[
                structure
            ] = self._clamp(
                current_structure_tolerance
                + biomechanical_delta
            )

        tolerance.last_learning_update = (
            learned_at
            or datetime.now(timezone.utc)
        )

        changes = [
            (
                "Tolérance physiologique : "
                f"{old_physiological:.1f} → "
                f"{tolerance.learned_physiological_tolerance_score:.1f}."
            ),
            (
                "Tolérance biomécanique : "
                f"{old_biomechanical:.1f} → "
                f"{tolerance.learned_biomechanical_tolerance_score:.1f}."
            ),
            (
                f"Tolérance {session_key} : "
                f"{tolerance.session_type_tolerance_scores[session_key]:.1f}."
            ),
        ]

        for structure in sensitive_structures:
            changes.append(
                f"Tolérance {structure} : "
                f"{tolerance.structure_tolerance_scores[structure]:.1f}."
            )

        return ToleranceLearningApplication(
            updated_profile=updated,
            applied=True,
            changes=changes,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return round(
            max(0.0, min(100.0, value)),
            1,
        )