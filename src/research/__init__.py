"""Infrastructure scientifique d’ATLAS OS."""

from .training_protocol import (
    EvidenceLevel,
    IntensityPattern,
    ProtocolApplicability,
    ProtocolBlockDefinition,
    ResearchReference,
    TrainingProtocolRegistry,
    TrainingResearchProtocol,
)
from .training_protocol_catalog import (
    build_default_training_protocol_registry,
    build_hill_sprints_protocol,
    build_mixed_threshold_vo2_protocol,
    build_triangular_vo2_protocol,
)
from .training_protocol_selector import (
    ProtocolSelection,
    TrainingProtocolSelector,
)

__all__ = [
    "EvidenceLevel",
    "IntensityPattern",
    "ProtocolApplicability",
    "ProtocolBlockDefinition",
    "ProtocolSelection",
    "ResearchReference",
    "TrainingProtocolRegistry",
    "TrainingProtocolSelector",
    "TrainingResearchProtocol",
    "build_default_training_protocol_registry",
    "build_hill_sprints_protocol",
    "build_mixed_threshold_vo2_protocol",
    "build_triangular_vo2_protocol",
]