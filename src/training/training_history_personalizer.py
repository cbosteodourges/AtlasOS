"""
ATLAS OS
Personnalisation du programme à partir de la mémoire FIT + Wellness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from statistics import mean, median
from typing import Any, Iterable

from src.performance.athlete_profile import AthleteProfile


@dataclass(slots=True)
class SessionToleranceEvidence:
    """Tolérance apprise pour une famille de séances."""

    session_type: str
    observation_count: int
    average_response_24h: float | None
    average_recovery_hours: float | None
    average_confidence_score: float
    tolerance_score: int


@dataclass(slots=True)
class TrainingHistoryPersonalization:
    """Décisions de génération tirées de l'historique individuel."""

    session_tolerance_scores: dict[str, float] = field(
        default_factory=dict
    )
    evidence: list[SessionToleranceEvidence] = field(
        default_factory=list
    )
    learned_response_count: int = 0
    cycling_sessions_per_week: int = 0
    maximum_weekly_progression_percent: float = 8.0
    recovery_days_after_intensity: float | None = None
    recovery_days_after_long_run: float | None = None
    acute_chronic_load_ratio: float | None = None
    explanations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class TrainingHistoryPersonalizer:
    """
    Transforme la mémoire FIT + Wellness en paramètres prudents.

    Les scores mesurent une tolérance observée. Ils ne prouvent pas
    qu'un type de séance cause à lui seul une amélioration.
    """

    PROTOCOL_SESSION_TYPES = {
        "hill_sprints": ("sprint_acceleration",),
        "mixed_threshold_vo2": ("sv2", "z3"),
        "triangular_vo2": ("vma",),
    }

    INTENSITY_TYPES = {
        "sprint_acceleration",
        "sv2",
        "z3",
        "vma",
        "hill_sprints",
        "mixed_threshold_vo2",
        "triangular_vo2",
    }

    def build(
        self,
        payload: dict[str, Any],
    ) -> TrainingHistoryPersonalization:
        """Construit les paramètres appris depuis le JSON fusionné."""
        activities = [
            item
            for item in payload.get("activities", [])
            if isinstance(item, dict)
            and bool(item.get("automatic_learning_allowed"))
        ]

        result = TrainingHistoryPersonalization(
            learned_response_count=len(activities),
            acute_chronic_load_ratio=self._number(
                payload.get("acute_chronic_load_ratio")
            ),
        )

        grouped = self._group_by_session_type(activities)
        evidence_by_type: dict[str, SessionToleranceEvidence] = {}

        for session_type, items in sorted(grouped.items()):
            evidence = self._summarize(session_type, items)
            evidence_by_type[session_type] = evidence
            result.evidence.append(evidence)
            result.session_tolerance_scores[
                session_type
            ] = evidence.tolerance_score

        for protocol_type, source_types in (
            self.PROTOCOL_SESSION_TYPES.items()
        ):
            source_evidence = [
                evidence_by_type[item]
                for item in source_types
                if item in evidence_by_type
            ]
            if not source_evidence:
                continue

            total = sum(
                item.observation_count
                for item in source_evidence
            )
            score = sum(
                item.tolerance_score * item.observation_count
                for item in source_evidence
            ) / total
            result.session_tolerance_scores[
                protocol_type
            ] = round(score, 1)

        intensity_recoveries = self._recovery_values(
            activities,
            self.INTENSITY_TYPES,
        )
        if intensity_recoveries:
            result.recovery_days_after_intensity = float(ceil(median(intensity_recoveries) / 24))

        long_run_recoveries = self._recovery_values(
            activities,
            {"long_run"},
        )
        if long_run_recoveries:
            result.recovery_days_after_long_run = float(ceil(median(long_run_recoveries) / 24))

        result.cycling_sessions_per_week = (
            self._cycling_recommendation(grouped)
        )
        result.maximum_weekly_progression_percent = (
            self._progression_limit(
                result.acute_chronic_load_ratio
            )
        )

        self._add_explanations(result, evidence_by_type)
        self._add_warnings(result)
        return result

    def apply(
        self,
        profile: AthleteProfile,
        personalization: TrainingHistoryPersonalization,
    ) -> AthleteProfile:
        """Injecte les apprentissages dans le profil sportif."""
        tolerance = profile.tolerance
        tolerance.session_type_tolerance_scores.update(
            personalization.session_tolerance_scores
        )
        tolerance.learned_response_count = max(
            tolerance.learned_response_count,
            personalization.learned_response_count,
        )

        if personalization.recovery_days_after_intensity is not None:
            tolerance.usual_recovery_days_after_intensity = (
                personalization.recovery_days_after_intensity
            )

        if personalization.recovery_days_after_long_run is not None:
            tolerance.usual_recovery_days_after_long_run = (
                personalization.recovery_days_after_long_run
            )

        if personalization.acute_chronic_load_ratio is not None:
            tolerance.recent_load_change_percent = round(
                (
                    personalization.acute_chronic_load_ratio
                    - 1.0
                )
                * 100,
                1,
            )

        return profile

    @staticmethod
    def _group_by_session_type(
        activities: Iterable[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in activities:
            session_type = str(
                item.get("session_type") or "unknown"
            )
            grouped.setdefault(session_type, []).append(item)
        return grouped

    def _summarize(
        self,
        session_type: str,
        items: list[dict[str, Any]],
    ) -> SessionToleranceEvidence:
        responses = self._numbers(
            item.get("response_24h")
            for item in items
        )
        recoveries = self._numbers(
            item.get("recovered_within_hours")
            for item in items
        )
        confidences = self._numbers(
            item.get("confidence_score")
            for item in items
        )

        average_response = (
            mean(responses) if responses else None
        )
        average_recovery = (
            mean(recoveries) if recoveries else None
        )
        average_confidence = (
            mean(confidences) if confidences else 50.0
        )

        score = 65.0
        if average_response is not None:
            score += max(-18.0, min(12.0, average_response * 2))
        if average_recovery is not None:
            score -= max(
                0.0,
                min(15.0, (average_recovery - 30.0) * 0.5),
            )

        score += (average_confidence - 70.0) * 0.10
        reliability = min(1.0, len(items) / 8.0)
        score = 50.0 + (score - 50.0) * reliability

        return SessionToleranceEvidence(
            session_type=session_type,
            observation_count=len(items),
            average_response_24h=(
                round(average_response, 1)
                if average_response is not None
                else None
            ),
            average_recovery_hours=(
                round(average_recovery, 1)
                if average_recovery is not None
                else None
            ),
            average_confidence_score=round(
                average_confidence,
                1,
            ),
            tolerance_score=round(
                max(0.0, min(100.0, score))
            ),
        )

    def _cycling_recommendation(
        self,
        grouped: dict[str, list[dict[str, Any]]],
    ) -> int:
        cycling = (
            grouped.get("cycling", [])
            + grouped.get("road", [])
        )
        if len(cycling) < 6:
            return 0

        responses = self._numbers(
            item.get("response_24h")
            for item in cycling
        )
        recoveries = self._numbers(
            item.get("recovered_within_hours")
            for item in cycling
        )
        response = mean(responses) if responses else None
        recovery = mean(recoveries) if recoveries else None

        if (
            (response is None or response >= -4.0)
            and (recovery is None or recovery <= 36.0)
        ):
            return 1
        return 0

    @staticmethod
    def _progression_limit(
        load_ratio: float | None,
    ) -> float:
        if load_ratio is None:
            return 8.0
        if load_ratio >= 1.30:
            return 5.0
        if load_ratio >= 1.15:
            return 6.0
        return 8.0

    def _add_explanations(
        self,
        result: TrainingHistoryPersonalization,
        evidence: dict[str, SessionToleranceEvidence],
    ) -> None:
        result.explanations.append(
            f"{result.learned_response_count} réponses FIT + Wellness "
            "fiables alimentent la personnalisation."
        )

        for name in ("z2", "z3", "sprint_acceleration"):
            item = evidence.get(name)
            if item is not None:
                result.explanations.append(
                    f"{name} : tolérance {item.tolerance_score}/100 "
                    f"sur {item.observation_count} observations."
                )

        for name in ("sv2", "vma"):
            item = evidence.get(name)
            if item is not None:
                result.explanations.append(
                    f"{name} : réponse à 24 h "
                    f"{item.average_response_24h} et récupération "
                    f"{item.average_recovery_hours} h en moyenne."
                )

        if result.cycling_sessions_per_week:
            result.explanations.append(
                "Une séance vélo hebdomadaire est retenue comme "
                "complément aérobie croisé."
            )

        if result.acute_chronic_load_ratio is not None:
            result.explanations.append(
                "Ratio descriptif de charge récente : "
                f"{result.acute_chronic_load_ratio:.2f}."
            )

    @staticmethod
    def _add_warnings(
        result: TrainingHistoryPersonalization,
    ) -> None:
        if result.learned_response_count < 20:
            result.warnings.append(
                "Historique fiable encore limité : personnalisation "
                "volontairement conservatrice."
            )

        if (
            result.acute_chronic_load_ratio is not None
            and result.acute_chronic_load_ratio >= 1.30
        ):
            result.warnings.append(
                "Charge récente supérieure à la référence de 28 jours : "
                "progression initiale limitée."
            )

        result.warnings.append(
            "Les associations historiques guident le programme sans "
            "être interprétées comme des preuves de causalité."
        )

    @classmethod
    def _recovery_values(
        cls,
        activities: Iterable[dict[str, Any]],
        session_types: set[str],
    ) -> list[float]:
        return cls._numbers(
            item.get("recovered_within_hours")
            for item in activities
            if str(item.get("session_type")) in session_types
        )

    @classmethod
    def _numbers(
        cls,
        values: Iterable[Any],
    ) -> list[float]:
        result = []
        for value in values:
            number = cls._number(value)
            if number is not None:
                result.append(number)
        return result

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None