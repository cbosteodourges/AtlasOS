"""
ATLAS OS
Orchestration de la boucle adaptative quotidienne Atlas Coach.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.atlas_brain import (
    AtlasIndexEngine,
    AtlasIndexResult,
)
from src.performance.athlete_profile import AthleteProfile
from src.physiology import (
    PhysiologyEngine,
    PhysiologyInput,
    PhysiologyResult,
)

from .adaptation_engine import (
    AdaptedWorkoutResult,
    WorkoutAdaptationEngine,
)
from .decision_engine import (
    TrainingDecision,
    TrainingDecisionEngine,
)
from .response_learning import (
    TrainingResponseLearning,
    TrainingResponseLearningEngine,
    TrainingResponseObservation,
)
from .session_models import AdaptiveWorkout
from .tolerance_learning import (
    AthleteToleranceLearningEngine,
    ToleranceLearningApplication,
)


@dataclass(slots=True)
class DailyAdaptiveTrainingResult:
    """Résultat complet avant la séance du jour."""

    physiology: PhysiologyResult
    atlas_index: AtlasIndexResult
    decision: TrainingDecision
    adaptation: AdaptedWorkoutResult


@dataclass(slots=True)
class AdaptiveLearningResult:
    """Réponse analysée et profil mis à jour."""

    response: TrainingResponseLearning
    profile_update: ToleranceLearningApplication


class AdaptiveTrainingLoop:
    """Relie récupération, indice, décision et apprentissage."""

    def __init__(self) -> None:
        self.physiology_engine = PhysiologyEngine()
        self.atlas_index_engine = AtlasIndexEngine()
        self.decision_engine = TrainingDecisionEngine()
        self.adaptation_engine = WorkoutAdaptationEngine()
        self.response_engine = (
            TrainingResponseLearningEngine()
        )
        self.tolerance_learning_engine = (
            AthleteToleranceLearningEngine()
        )

    def prepare_session(
        self,
        physiology_input: PhysiologyInput,
        planned_workout: AdaptiveWorkout,
        *,
        mechanical_risk_score: Optional[float] = None,
        mechanical_data_confidence: Optional[float] = None,
    ) -> DailyAdaptiveTrainingResult:
        """Prépare et adapte la séance avant sa réalisation."""
        physiology = self.physiology_engine.analyze(
            physiology_input
        )
        atlas_index = self.atlas_index_engine.calculate(
            physiology,
            mechanical_risk_score=mechanical_risk_score,
            mechanical_data_confidence=(
                mechanical_data_confidence
            ),
        )
        decision = self.decision_engine.decide(
            atlas_index,
            planned_workout,
        )
        adaptation = self.adaptation_engine.adapt(
            planned_workout,
            decision,
        )

        return DailyAdaptiveTrainingResult(
            physiology=physiology,
            atlas_index=atlas_index,
            decision=decision,
            adaptation=adaptation,
        )

    def learn_from_response(
        self,
        preparation: DailyAdaptiveTrainingResult,
        observations: list[TrainingResponseObservation],
        *,
        pre_session_pain_0_10: Optional[float] = None,
    ) -> TrainingResponseLearning:
        """Analyse la réponse à 24–72 heures."""
        return self.response_engine.analyze(
            preparation.adaptation.adapted_workout,
            observations,
            pre_session_recovery_score=(
                preparation.physiology.recovery_score
            ),
            pre_session_atlas_index_score=(
                preparation.atlas_index.score
            ),
            pre_session_pain_0_10=(
                pre_session_pain_0_10
            ),
        )

    def learn_and_update_profile(
        self,
        preparation: DailyAdaptiveTrainingResult,
        observations: list[TrainingResponseObservation],
        profile: AthleteProfile,
        *,
        pre_session_pain_0_10: Optional[float] = None,
    ) -> AdaptiveLearningResult:
        """Ferme la boucle et mémorise la tolérance apprise."""
        response = self.learn_from_response(
            preparation,
            observations,
            pre_session_pain_0_10=(
                pre_session_pain_0_10
            ),
        )
        profile_update = (
            self.tolerance_learning_engine.apply(
                profile,
                preparation.adaptation.adapted_workout,
                response,
            )
        )

        return AdaptiveLearningResult(
            response=response,
            profile_update=profile_update,
        )