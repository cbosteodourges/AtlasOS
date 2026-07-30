"""
ATLAS OS
Package biomécanique.
"""

from src.biomechanics.biomechanical_engine import (
    BiomechanicalEngine,
    BiomechanicalReport,
    PainBiomechanicalAnalysis,
)
from src.biomechanics.exercise_engine import (
    BiomechanicalExercise,
    ExerciseEngine,
)
from src.biomechanics.joint_analyzer import (
    JointAnalyzer,
    JointFinding,
    JointProfile,
)
from src.biomechanics.kinetic_chain import (
    KineticChain,
    KineticChainAnalyzer,
    KineticChainFinding,
)
from src.biomechanics.movement_patterns import (
    MovementPattern,
    build_default_movement_patterns,
)
from src.biomechanics.muscle_analyzer import (
    MuscleAnalyzer,
    MuscleFinding,
    MuscleProfile,
)
from src.biomechanics.pain_mapper import (
    PainMapper,
    PainMappingResult,
)
from src.biomechanics.risk_analyzer import (
    BiomechanicalRiskAnalyzer,
    BiomechanicalRiskResult,
)


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — EXPORTS PUBLICS
# ████████████████████████████████████████████████████████████

__all__ = [
    "BiomechanicalEngine",
    "BiomechanicalExercise",
    "BiomechanicalReport",
    "BiomechanicalRiskAnalyzer",
    "BiomechanicalRiskResult",
    "ExerciseEngine",
    "JointAnalyzer",
    "JointFinding",
    "JointProfile",
    "KineticChain",
    "KineticChainAnalyzer",
    "KineticChainFinding",
    "MovementPattern",
    "MuscleAnalyzer",
    "MuscleFinding",
    "MuscleProfile",
    "PainBiomechanicalAnalysis",
    "PainMapper",
    "PainMappingResult",
    "build_default_movement_patterns",
]


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████