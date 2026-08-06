"""
ATLAS OS
Moteur Performance.
"""

from src.performance.activity_adapter import (
    LongitudinalActivityAdapter,
    TrainingActivityAdapter,
)
from src.performance.adaptive_preparation_analyzer import (
    AdaptivePreparationAnalyzer,
)
from src.performance.athlete_profile import (
    AthleteProfile,
    EvolvingThreshold,
    PhysiologicalReferences,
    ThresholdHistoryEntry,
    TrainingAvailability,
    TrainingTolerance,
)
from src.performance.athlete_profile_builder import (
    AthleteProfileBuilder,
)
from src.performance.competition_analyzer import (
    CompetitionPreparationAnalyzer,
)
from src.performance.competition_models import (
    AdaptivePreparationPeriod,
    CompetitionComparison,
    CompetitionEvent,
    CompetitionPreparationAnalysis,
    PreparationPhaseSummary,
    PreparationWindowSummary,
    TaperSummary,
)
from src.performance.detailed_session_analyzer import (
    DetailedSessionAnalyzer,
)
from src.performance.history_analyzer import (
    TrainingHistoryAnalyzer,
    display_history_analysis,
)
from src.performance.insight_models import (
    DistancePerformanceBenchmark,
    PerformanceInsightAnalysis,
    PerformanceWindowSummary,
)
from src.performance.longitudinal_analyzer import (
    LongitudinalPerformanceAnalyzer,
)
from src.performance.longitudinal_models import (
    EnergyMetrics,
    EnvironmentMetrics,
    LongitudinalActivity,
    LongitudinalAnalysis,
    RecoveryMetrics,
    RunningDynamics,
    WeeklyPerformanceSummary,
)
from src.performance.models import (
    HistoryAnalysis,
    PerformanceGoal,
    PlannedWorkout,
    TrainingActivity,
    TrainingPlan,
    TrainingWeek,
    TrainingZone,
)
from src.performance.performance_insight_analyzer import (
    PerformanceInsightAnalyzer,
)
from src.performance.planner import (
    RunningPlanGenerator,
    display_training_plan,
)
from src.performance.session_fingerprint import (
    AthleteSessionLearning,
    DataIntegrityAssessment,
    DetailedSessionAnalysis,
    SessionBlock,
    SessionFingerprint,
    SessionTypeEffectiveness,
    ThresholdObservation,
    WorkoutExecutionSummary,
)
from src.performance.session_fingerprint_builder import (
    SessionFingerprintBuilder,
)
from src.performance.threshold_evolution_analyzer import (
    ThresholdEvolutionAnalyzer,
)
from src.performance.zones import (
    TrainingZonesEngine,
    format_pace,
)

__all__ = [
    "AdaptivePreparationAnalyzer",
    "AdaptivePreparationPeriod",
    "AthleteProfile",
    "EvolvingThreshold",
    "AthleteProfileBuilder",
    "AthleteSessionLearning",
    "DataIntegrityAssessment",
    "DetailedSessionAnalysis",
    "DetailedSessionAnalyzer",
    "CompetitionComparison",
    "CompetitionEvent",
    "CompetitionPreparationAnalysis",
    "CompetitionPreparationAnalyzer",
    "DistancePerformanceBenchmark",
    "EnergyMetrics",
    "EnvironmentMetrics",
    "HistoryAnalysis",
    "LongitudinalActivity",
    "LongitudinalActivityAdapter",
    "TrainingActivityAdapter",
    "LongitudinalAnalysis",
    "LongitudinalPerformanceAnalyzer",
    "PerformanceGoal",
    "PerformanceInsightAnalysis",
    "PerformanceInsightAnalyzer",
    "PerformanceWindowSummary",
    "PhysiologicalReferences",
    "PlannedWorkout",
    "PreparationPhaseSummary",
    "PreparationWindowSummary",
    "RecoveryMetrics",
    "RunningDynamics",
    "RunningPlanGenerator",
    "SessionBlock",
    "SessionFingerprint",
    "SessionFingerprintBuilder",
    "SessionTypeEffectiveness",
    "ThresholdEvolutionAnalyzer",
    "ThresholdHistoryEntry",
    "ThresholdObservation",
    "WorkoutExecutionSummary",
    "TaperSummary",
    "TrainingActivity",
    "TrainingAvailability",
    "TrainingHistoryAnalyzer",
    "TrainingPlan",
    "TrainingTolerance",
    "TrainingWeek",
    "TrainingZone",
    "TrainingZonesEngine",
    "WeeklyPerformanceSummary",
    "display_history_analysis",
    "display_training_plan",
    "format_pace",
]