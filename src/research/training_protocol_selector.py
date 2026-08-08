"""Sélection individualisée des protocoles Atlas Research."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.performance.athlete_profile import AthleteProfile

from .training_protocol import (
    TrainingProtocolRegistry,
    TrainingResearchProtocol,
)


@dataclass(slots=True)
class ProtocolSelection:
    """Résultat explicable du classement d’un protocole."""

    protocol: TrainingResearchProtocol
    suitability_score: int
    evidence_score: int
    tolerance_score: int
    missing_metrics: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class TrainingProtocolSelector:
    """Classe les protocoles selon le contexte réel de l’athlète."""

    def __init__(
        self,
        registry: TrainingProtocolRegistry,
    ) -> None:
        self._registry = registry

    def select(
        self,
        *,
        profile: AthleteProfile,
        phase: str,
        goal_distance_km: float,
        available_dynamic_metrics: set[str] | None = None,
    ) -> list[ProtocolSelection]:
        """Retourne les protocoles compatibles, du meilleur au moins bon."""
        athlete_level = (
            profile.observed_level
            or profile.declared_level
        )
        protocols = self._registry.find_applicable(
            phase=phase,
            goal_distance_km=goal_distance_km,
            athlete_level=athlete_level,
        )
        available_metrics = self._available_metrics(
            profile,
            available_dynamic_metrics or set(),
        )
        selections = []

        for protocol in protocols:
            if self._must_exclude_for_pain(profile, protocol):
                continue

            missing_metrics = [
                metric
                for metric in protocol.applicability.required_metrics
                if metric not in available_metrics
            ]
            tolerance_score = self._tolerance_score(
                profile,
                protocol,
            )
            warnings = self._warnings(
                profile,
                protocol,
                missing_metrics,
                tolerance_score,
            )
            suitability_score = self._suitability_score(
                profile,
                protocol,
                tolerance_score,
                missing_metrics,
            )
            reasons = [
                (
                    "Niveau sportif compatible : "
                    f"{athlete_level}."
                ),
                (
                    "Confiance scientifique : "
                    f"{protocol.evidence_confidence_score}/100."
                ),
                (
                    "Tolérance individuelle estimée : "
                    f"{tolerance_score}/100."
                ),
            ]

            selections.append(
                ProtocolSelection(
                    protocol=protocol,
                    suitability_score=suitability_score,
                    evidence_score=(
                        protocol.evidence_confidence_score
                    ),
                    tolerance_score=tolerance_score,
                    missing_metrics=missing_metrics,
                    warnings=warnings,
                    reasons=reasons,
                )
            )

        return sorted(
            selections,
            key=lambda item: (
                -item.suitability_score,
                -item.evidence_score,
                item.protocol.protocol_id,
            ),
        )

    @staticmethod
    def _available_metrics(
        profile: AthleteProfile,
        dynamic_metrics: set[str],
    ) -> set[str]:
        metrics = set(dynamic_metrics)
        physiological = profile.physiological

        if physiological.vma_kmh is not None:
            metrics.add("vma")

        if (
            physiological.threshold_speed_kmh is not None
            or physiological.sv2.speed_kmh is not None
        ):
            metrics.add("individual_threshold_speed")

        if profile.data_quality_score > 0:
            metrics.add("training_history")

        if (
            profile.tolerance.learned_response_count > 0
            or profile.history_activity_count > 0
        ):
            metrics.add("biomechanical_tolerance")

        if not profile.current_pain_or_injury:
            metrics.add("pain_status")

        return metrics

    @staticmethod
    def _must_exclude_for_pain(
        profile: AthleteProfile,
        protocol: TrainingResearchProtocol,
    ) -> bool:
        if not profile.current_pain_or_injury:
            return False

        return any(
            (
                "douleur" in contraindication
                or "injury" in contraindication
            )
            for contraindication
            in protocol.applicability.contraindications
        )

    @staticmethod
    def _tolerance_score(
        profile: AthleteProfile,
        protocol: TrainingResearchProtocol,
    ) -> int:
        tolerance = profile.tolerance
        learned_for_type = (
            tolerance.session_type_tolerance_scores.get(
                protocol.workout_type_key
            )
        )

        if learned_for_type is not None:
            return round(
                max(0, min(100, learned_for_type))
            )

        physiological = (
            tolerance.learned_physiological_tolerance_score
        )
        biomechanical = (
            tolerance.learned_biomechanical_tolerance_score
        )

        if protocol.workout_type_key == "hill_sprints":
            score = (
                physiological * 0.35
                + biomechanical * 0.65
            )
        else:
            score = (
                physiological * 0.65
                + biomechanical * 0.35
            )

        return round(max(0, min(100, score)))

    @staticmethod
    def _suitability_score(
        profile: AthleteProfile,
        protocol: TrainingResearchProtocol,
        tolerance_score: int,
        missing_metrics: list[str],
    ) -> int:
        confidence = max(
            0,
            min(100, profile.profile_confidence_score),
        )
        score = (
            protocol.evidence_confidence_score * 0.55
            + tolerance_score * 0.35
            + confidence * 0.10
            - len(missing_metrics) * 8
        )

        return round(max(0, min(100, score)))

    @staticmethod
    def _warnings(
        profile: AthleteProfile,
        protocol: TrainingResearchProtocol,
        missing_metrics: list[str],
        tolerance_score: int,
    ) -> list[str]:
        warnings = []

        if missing_metrics:
            warnings.append(
                "Mesures manquantes : "
                + ", ".join(missing_metrics)
                + "."
            )

        if tolerance_score < 50:
            warnings.append(
                "Tolérance individuelle insuffisamment favorable."
            )

        if profile.profile_confidence_score < 60:
            warnings.append(
                "Profil sportif encore insuffisamment documenté."
            )

        if protocol.evidence_confidence_score < 60:
            warnings.append(
                "Protocole Atlas encore expérimental."
            )

        return warnings