"""Moteur d’entraînement adaptatif d’ATLAS OS."""

from .adaptation_engine import (
    AdaptedWorkoutResult,
    WorkoutAdaptationEngine,
)
from .adaptive_loop import (
    AdaptiveLearningResult,
    AdaptiveTrainingLoop,
    DailyAdaptiveTrainingResult,
)
from .decision_engine import (
    TrainingDecision,
    TrainingDecisionAction,
    TrainingDecisionEngine,
)
from .program_models import (
    AdaptiveTrainingProgram,
    AdaptiveTrainingWeek,
    ProgramGenerationSettings,
    TrainingPhase,
)
from .program_phase_planner import (
    ProgramPhasePlan,
    ProgramPhasePlanner,
)
from .research_workout_builder import (
    ResearchWorkoutBuilder,
)
from .response_learning import (
    TrainingResponseLearning,
    TrainingResponseLearningEngine,
    TrainingResponseObservation,
    TrainingResponseOutcome,
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
from .tolerance_learning import (
    AthleteToleranceLearningEngine,
    ToleranceLearningApplication,
)

__all__ = [
    "AdaptedWorkoutResult",
    "AdaptiveLearningResult",
    "AdaptiveTrainingLoop",
    "AdaptiveTrainingProgram",
    "AdaptiveTrainingWeek",
    "AdaptiveWorkout",
    "AthleteToleranceLearningEngine",
    "BlockType",
    "DailyAdaptiveTrainingResult",
    "ExpectedTrainingResponse",
    "IntensityTarget",
    "ProgramGenerationSettings",
    "ProgramPhasePlan",
    "ProgramPhasePlanner",
    "ResearchWorkoutBuilder",
    "ToleranceLearningApplication",
    "TrainingBlock",
    "TrainingDecision",
    "TrainingDecisionAction",
    "TrainingDecisionEngine",
    "TrainingPhase",
    "TrainingResponseLearning",
    "TrainingResponseLearningEngine",
    "TrainingResponseObservation",
    "TrainingResponseOutcome",
    "WorkoutAdaptationEngine",
    "WorkoutPriority",
    "WorkoutType",
]