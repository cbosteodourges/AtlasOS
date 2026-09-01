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
from .program_generator import (
    TrainingProgramGenerator,
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
from .program_validator import (
    ProgramValidationError,
    ProgramValidationIssue,
    ProgramValidationReport,
    TrainingProgramValidator,
)
from .program_revision_engine import (
    TrainingProgramChange,
    TrainingProgramRevisionEngine,
    TrainingProgramRevisionProposal,
)
from .research_workout_builder import (
    ResearchWorkoutBuilder,
)
from .training_program_loader import (
    TrainingProgramLoader,
)
from .workout_execution_matcher import (
    AtlasWorkoutExecutionMatch,
    AtlasWorkoutExecutionMatcher,
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
from .standard_workout_builder import (
    StandardWorkoutBuilder,
)
from .training_history_personalizer import (
    SessionToleranceEvidence,
    TrainingHistoryPersonalization,
    TrainingHistoryPersonalizer,
)
from .tolerance_learning import (
    AthleteToleranceLearningEngine,
    ToleranceLearningApplication,
)

__all__ = [
    "AdaptedWorkoutResult",
    "AtlasWorkoutExecutionMatch",
    "AtlasWorkoutExecutionMatcher",
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
    "ProgramValidationError",
    "ProgramValidationIssue",
    "ProgramValidationReport",
    "ResearchWorkoutBuilder",
    "StandardWorkoutBuilder",
    "ToleranceLearningApplication",
    "TrainingBlock",
    "TrainingDecision",
    "TrainingDecisionAction",
    "TrainingDecisionEngine",
    "TrainingHistoryPersonalization",
    "TrainingHistoryPersonalizer",
    "SessionToleranceEvidence",
    "TrainingPhase",
    "TrainingProgramGenerator",
    "TrainingProgramValidator",
    "TrainingProgramLoader",
    "TrainingProgramChange",
    "TrainingProgramRevisionEngine",
    "TrainingProgramRevisionProposal",
    "TrainingResponseLearning",
    "TrainingResponseLearningEngine",
    "TrainingResponseObservation",
    "TrainingResponseOutcome",
    "WorkoutAdaptationEngine",
    "WorkoutPriority",
    "WorkoutType",
]