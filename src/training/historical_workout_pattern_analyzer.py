"""
ATLAS OS
Extraction explicable des structures d'entraînement historiques.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Any


@dataclass(slots=True)
class HistoricalWorkoutPattern:
    """Structure de séance réellement observée."""

    pattern_type: str
    source_activity_id: str
    source_date: str
    reference_event_title: str | None = None
    reference_outcome: str | None = None
    days_before_event: int | None = None
    comparable_distance: bool = False
    repetitions: int = 0
    work_distance_meters: int | None = None
    average_work_speed_kmh: float | None = None
    average_recovery_seconds: int | None = None
    group_distances_meters: list[int] = field(
        default_factory=list
    )
    confidence_score: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HistoricalWorkoutPatternMemory:
    """Mémoire des structures fiables extraites."""

    activities_analyzed: int = 0
    patterns: list[HistoricalWorkoutPattern] = field(
        default_factory=list
    )
    warnings: list[str] = field(default_factory=list)


class HistoricalWorkoutPatternAnalyzer:
    """Analyse tous les FIT détaillés sans confondre les tours automatiques."""

    MINIMUM_ACTIVITY_CONFIDENCE = 70
    MINIMUM_BLOCK_CONFIDENCE = 70

    def analyze(
        self,
        payload: dict[str, Any],
        *,
        vma_kmh: float | None,
        goal_speed_kmh: float | None,
        goal_distance_km: float | None = None,
        competition_payload: dict[str, Any] | None = None,
        competition_lookback_days: int = 160,
    ) -> HistoricalWorkoutPatternMemory:
        analyses = {
            str(item.get("activity_id")): item
            for item in payload.get("analyses", [])
            if isinstance(item, dict)
        }
        eligible = [
            activity
            for activity in payload.get("activities", [])
            if isinstance(activity, dict)
            and str(activity.get("sport", "")).lower()
            == "running"
            and self._number(
                activity.get("confidence_score"),
                0,
            )
            >= self.MINIMUM_ACTIVITY_CONFIDENCE
            and str(activity.get("activity_id")) in analyses
        ]
        result = HistoricalWorkoutPatternMemory(
            activities_analyzed=len(eligible)
        )

        for activity in eligible:
            activity_id = str(activity["activity_id"])
            blocks = [
                block
                for block in analyses[activity_id].get(
                    "blocks",
                    [],
                )
                if isinstance(block, dict)
                and self._number(
                    block.get("confidence_score"),
                    100,
                )
                >= self.MINIMUM_BLOCK_CONFIDENCE
            ]
            source_date = str(
                activity.get("start_time", "")
            )[:10]
            context = self._competition_context(
                source_date,
                competition_payload,
                goal_distance_km=goal_distance_km,
                lookback_days=competition_lookback_days,
            )
            if (
                context is not None
                and context["days_before_event"] == 0
            ):
                continue

            short = self._interval_pattern(
                blocks,
                activity_id=activity_id,
                source_date=source_date,
                pattern_type="short_intervals",
                minimum_distance=150,
                maximum_distance=500,
                accepted_types={
                    "vma",
                    "sprint",
                    "sprint_acceleration",
                },
                minimum_speed=(
                    vma_kmh * 0.92
                    if vma_kmh is not None
                    else None
                ),
                minimum_repetitions=4,
            )
            if short is not None:
                result.patterns.append(
                    self._with_context(short, context)
                )

            threshold = self._interval_pattern(
                blocks,
                activity_id=activity_id,
                source_date=source_date,
                pattern_type="threshold_intervals",
                minimum_distance=800,
                maximum_distance=1200,
                accepted_types={"sv2"},
                minimum_speed=(
                    vma_kmh * 0.86
                    if vma_kmh is not None
                    else None
                ),
                minimum_repetitions=3,
            )
            if threshold is not None:
                result.patterns.append(
                    self._with_context(threshold, context)
                )

            long_specific = self._long_specific_pattern(
                blocks,
                activity_id=activity_id,
                source_date=source_date,
                goal_speed_kmh=goal_speed_kmh,
            )
            if long_specific is not None:
                result.patterns.append(
                    self._with_context(long_specific, context)
                )

        result.patterns.sort(
            key=lambda item: (
                item.source_date,
                item.pattern_type,
            )
        )
        if not result.patterns:
            result.warnings.append(
                "Aucune structure historique suffisamment fiable."
            )
        return result

    def _interval_pattern(
        self,
        blocks: list[dict[str, Any]],
        *,
        activity_id: str,
        source_date: str,
        pattern_type: str,
        minimum_distance: int,
        maximum_distance: int,
        accepted_types: set[str],
        minimum_speed: float | None,
        minimum_repetitions: int,
    ) -> HistoricalWorkoutPattern | None:
        work = [
            block
            for block in blocks
            if minimum_distance
            <= self._number(
                block.get("distance_meters"),
                0,
            )
            <= maximum_distance
            and (
                str(block.get("block_type", "")).lower()
                in accepted_types
                or (
                    minimum_speed is not None
                    and self._number(
                        block.get("average_speed_kmh"),
                        0,
                    )
                    >= minimum_speed
                )
            )
        ]
        if len(work) < minimum_repetitions:
            return None

        distances = [
            round(self._number(
                block.get("distance_meters"),
                0,
            ))
            for block in work
        ]
        dominant_distance = round(
            mean(distances) / 50
        ) * 50
        matching = [
            block
            for block, distance in zip(work, distances)
            if abs(distance - dominant_distance) <= 75
        ]
        if len(matching) < minimum_repetitions:
            return None

        recoveries = [
            self._number(
                block.get("duration_seconds"),
                0,
            )
            for block in blocks
            if str(block.get("block_type", "")).lower()
            in {"recovery", "z1"}
            and self._number(
                block.get("duration_seconds"),
                0,
            )
            > 0
        ]
        speeds = [
            self._number(
                block.get("average_speed_kmh"),
                0,
            )
            for block in matching
            if self._number(
                block.get("average_speed_kmh"),
                0,
            )
            > 0
        ]

        return HistoricalWorkoutPattern(
            pattern_type=pattern_type,
            source_activity_id=activity_id,
            source_date=source_date,
            repetitions=len(matching),
            work_distance_meters=dominant_distance,
            average_work_speed_kmh=(
                round(mean(speeds), 2)
                if speeds else None
            ),
            average_recovery_seconds=(
                round(mean(recoveries))
                if recoveries else None
            ),
            confidence_score=90,
            reasons=[
                (
                    f"{len(matching)} répétitions homogènes "
                    f"d'environ {dominant_distance} m détectées."
                )
            ],
        )

    def _long_specific_pattern(
        self,
        blocks: list[dict[str, Any]],
        *,
        activity_id: str,
        source_date: str,
        goal_speed_kmh: float | None,
    ) -> HistoricalWorkoutPattern | None:
        if goal_speed_kmh is None:
            return None

        minimum_speed = goal_speed_kmh * 0.90
        maximum_speed = goal_speed_kmh * 1.08
        groups: list[int] = []
        current_distance = 0
        speeds: list[float] = []

        for block in blocks:
            distance = round(self._number(
                block.get("distance_meters"),
                0,
            ))
            speed = self._number(
                block.get("average_speed_kmh"),
                0,
            )
            block_type = str(
                block.get("block_type", "")
            ).lower()
            specific = (
                800 <= distance <= 1200
                and block_type in {"z3", "sv2"}
                and minimum_speed <= speed <= maximum_speed
            )

            if specific:
                current_distance += distance
                speeds.append(speed)
            else:
                if current_distance >= 2000:
                    groups.append(current_distance)
                current_distance = 0

        if current_distance >= 2000:
            groups.append(current_distance)

        if not groups:
            return None

        return HistoricalWorkoutPattern(
            pattern_type="long_race_specific",
            source_activity_id=activity_id,
            source_date=source_date,
            repetitions=len(groups),
            average_work_speed_kmh=(
                round(mean(speeds), 2)
                if speeds else None
            ),
            group_distances_meters=groups,
            confidence_score=85,
            reasons=[
                (
                    "Blocs continus proches de l'allure "
                    "de compétition détectés."
                )
            ],
        )

    @staticmethod
    def _with_context(
        pattern: HistoricalWorkoutPattern,
        context: dict[str, Any] | None,
    ) -> HistoricalWorkoutPattern:
        if context is None:
            return pattern

        pattern.reference_event_title = str(
            context["title"]
        )
        pattern.reference_outcome = str(
            context["outcome"]
        )
        pattern.days_before_event = int(
            context["days_before_event"]
        )
        pattern.comparable_distance = bool(
            context["comparable_distance"]
        )
        pattern.reasons.append(
            (
                f"Séance réalisée {pattern.days_before_event} "
                f"jour(s) avant {pattern.reference_event_title}."
            )
        )
        return pattern

    @staticmethod
    def _competition_context(
        source_date: str,
        competition_payload: dict[str, Any] | None,
        *,
        goal_distance_km: float | None,
        lookback_days: int,
    ) -> dict[str, Any] | None:
        if not competition_payload or not source_date:
            return None

        try:
            activity_day = datetime.fromisoformat(
                source_date
            ).date()
        except ValueError:
            return None

        candidates = []

        for analysis in competition_payload.get(
            "analyses",
            [],
        ):
            if not isinstance(analysis, dict):
                continue

            event = analysis.get("event", {})
            if not isinstance(event, dict):
                continue

            try:
                event_day = datetime.fromisoformat(
                    str(event.get("event_date", ""))
                ).date()
                event_distance = float(
                    event.get("distance_km")
                )
            except (TypeError, ValueError):
                continue

            days_before = (event_day - activity_day).days
            if not 0 <= days_before <= lookback_days:
                continue

            comparable = False
            if goal_distance_km is not None:
                tolerance = max(
                    1.0,
                    goal_distance_km * 0.15,
                )
                comparable = (
                    abs(event_distance - goal_distance_km)
                    <= tolerance
                )

            candidates.append({
                "title": event.get("title", ""),
                "outcome": event.get("outcome", ""),
                "days_before_event": days_before,
                "comparable_distance": comparable,
            })

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda item: item["days_before_event"],
        )
    @staticmethod
    def _number(
        value: Any,
        default: float,
    ) -> float:
        if value is None or isinstance(value, bool):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default