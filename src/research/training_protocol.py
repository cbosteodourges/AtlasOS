"""
ATLAS OS
Protocoles scientifiques structurés pour Atlas Research.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class EvidenceLevel(str, Enum):
    """Nature principale des preuves disponibles."""

    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    RANDOMIZED_TRIAL = "randomized_trial"
    CROSSOVER_TRIAL = "crossover_trial"
    OBSERVATIONAL = "observational"
    EXPERT_CONSENSUS = "expert_consensus"
    EMERGING = "emerging"


class IntensityPattern(str, Enum):
    """Organisation de l’intensité dans un bloc."""

    CONSTANT = "constant"
    PROGRESSIVE = "progressive"
    VARIABLE = "variable"
    TRIANGULAR = "triangular"
    HILL_ACCELERATION = "hill_acceleration"


@dataclass(slots=True)
class ResearchReference:
    """Référence scientifique traçable."""

    title: str
    year: int
    authors: str = ""
    journal: str = ""
    doi: str = ""
    url: str = ""
    evidence_level: EvidenceLevel = (
        EvidenceLevel.EMERGING
    )


@dataclass(slots=True)
class ProtocolBlockDefinition:
    """Bloc générique décrit par la littérature."""

    name: str
    repetitions: int = 1
    duration_seconds: Optional[int] = None
    distance_meters: Optional[int] = None
    recovery_seconds: Optional[int] = None

    intensity_basis: str = ""
    intensity_min_percent: Optional[float] = None
    intensity_max_percent: Optional[float] = None
    intensity_pattern: IntensityPattern = (
        IntensityPattern.CONSTANT
    )

    gradient_min_percent: Optional[float] = None
    gradient_max_percent: Optional[float] = None
    instructions: str = ""

    def validate(self) -> None:
        if self.repetitions < 1:
            raise ValueError(
                "repetitions doit être supérieur ou égal à 1."
            )
        if (
            self.duration_seconds is None
            and self.distance_meters is None
        ):
            raise ValueError(
                "Un bloc doit définir une durée ou une distance."
            )
        if (
            self.duration_seconds is not None
            and self.duration_seconds <= 0
        ):
            raise ValueError(
                "duration_seconds doit être positive."
            )
        if (
            self.distance_meters is not None
            and self.distance_meters <= 0
        ):
            raise ValueError(
                "distance_meters doit être positive."
            )
        if (
            self.recovery_seconds is not None
            and self.recovery_seconds < 0
        ):
            raise ValueError(
                "recovery_seconds ne peut pas être négative."
            )


@dataclass(slots=True)
class ProtocolApplicability:
    """Conditions générales d’utilisation du protocole."""

    suitable_phases: list[str] = field(
        default_factory=list
    )
    suitable_goal_distances_km: list[float] = field(
        default_factory=list
    )
    suitable_athlete_levels: list[str] = field(
        default_factory=list
    )

    minimum_sessions_per_week: Optional[int] = None
    maximum_sessions_per_week: int = 1
    minimum_recovery_hours: int = 24
    maximum_recovery_hours: int = 72

    required_metrics: list[str] = field(
        default_factory=list
    )
    contraindications: list[str] = field(
        default_factory=list
    )


@dataclass(slots=True)
class TrainingResearchProtocol:
    """Protocole exploitable par Atlas Brain et Atlas Coach."""

    protocol_id: str
    version: str
    title: str
    workout_type_key: str
    summary: str

    objectives: list[str]
    blocks: list[ProtocolBlockDefinition]
    applicability: ProtocolApplicability

    expected_adaptations: list[str] = field(
        default_factory=list
    )
    known_risks: list[str] = field(
        default_factory=list
    )
    references: list[ResearchReference] = field(
        default_factory=list
    )

    evidence_confidence_score: int = 0
    last_reviewed_at: Optional[date] = None
    research_notes: list[str] = field(
        default_factory=list
    )

    def validate(self) -> None:
        if not self.protocol_id.strip():
            raise ValueError("protocol_id est obligatoire.")
        if not self.version.strip():
            raise ValueError("version est obligatoire.")
        if not self.title.strip():
            raise ValueError("title est obligatoire.")
        if not 0 <= self.evidence_confidence_score <= 100:
            raise ValueError(
                "evidence_confidence_score doit être "
                "compris entre 0 et 100."
            )
        if not self.blocks:
            raise ValueError(
                "Un protocole doit contenir au moins un bloc."
            )
        for block in self.blocks:
            block.validate()


class TrainingProtocolRegistry:
    """Catalogue versionné des protocoles Atlas Research."""

    def __init__(self) -> None:
        self._protocols: dict[
            str,
            TrainingResearchProtocol,
        ] = {}

    def register(
        self,
        protocol: TrainingResearchProtocol,
    ) -> None:
        """Ajoute ou remplace une version de protocole."""
        protocol.validate()
        self._protocols[protocol.protocol_id] = protocol

    def get(
        self,
        protocol_id: str,
    ) -> TrainingResearchProtocol:
        """Retourne un protocole par son identifiant."""
        try:
            return self._protocols[protocol_id]
        except KeyError as error:
            raise KeyError(
                f"Protocole Atlas Research inconnu : "
                f"{protocol_id}"
            ) from error

    def list_all(
        self,
    ) -> list[TrainingResearchProtocol]:
        """Retourne tous les protocoles enregistrés."""
        return sorted(
            self._protocols.values(),
            key=lambda item: item.protocol_id,
        )

    def find_applicable(
        self,
        *,
        phase: str,
        goal_distance_km: float,
        athlete_level: str,
    ) -> list[TrainingResearchProtocol]:
        """Préfiltre les protocoles compatibles avec le contexte."""
        applicable = []

        for protocol in self._protocols.values():
            rules = protocol.applicability

            phase_matches = (
                not rules.suitable_phases
                or phase in rules.suitable_phases
            )
            distance_matches = (
                not rules.suitable_goal_distances_km
                or goal_distance_km
                in rules.suitable_goal_distances_km
            )
            level_matches = (
                not rules.suitable_athlete_levels
                or athlete_level
                in rules.suitable_athlete_levels
            )

            if (
                phase_matches
                and distance_matches
                and level_matches
            ):
                applicable.append(protocol)

        return sorted(
            applicable,
            key=lambda item: (
                -item.evidence_confidence_score,
                item.protocol_id,
            ),
        )