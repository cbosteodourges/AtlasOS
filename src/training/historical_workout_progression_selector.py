"""
ATLAS OS
Sélection d'une progression depuis les séances historiquement réussies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .historical_workout_pattern_analyzer import (
    HistoricalWorkoutPattern,
)


@dataclass(slots=True)
class HistoricalWorkoutPrescription:
    """Séance historique normalisée pour le générateur."""

    kind: str
    repetitions: int = 0
    work_distance_meters: int | None = None
    threshold_distance_meters: int | None = None
    vo2_distance_meters: int | None = None
    group_distances_meters: list[int] = field(
        default_factory=list
    )
    source_activity_ids: list[str] = field(
        default_factory=list
    )
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HistoricalWorkoutProgression:
    """Progression qualitative répartie par phase."""

    base: list[HistoricalWorkoutPrescription] = field(
        default_factory=list
    )
    development: list[
        HistoricalWorkoutPrescription
    ] = field(default_factory=list)
    specific: list[HistoricalWorkoutPrescription] = field(
        default_factory=list
    )
    warnings: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return bool(
            self.base
            or self.development
            or self.specific
        )


class HistoricalWorkoutProgressionSelector:
    """Transforme les motifs réussis en progression variée."""

    MINIMUM_CONFIDENCE = 70

    def build(
        self,
        patterns: list[HistoricalWorkoutPattern],
    ) -> HistoricalWorkoutProgression:
        reliable = [
            item
            for item in patterns
            if item.reference_outcome is not None
            and item.reference_outcome.startswith("successful")
            and item.comparable_distance
            and item.confidence_score
            >= self.MINIMUM_CONFIDENCE
        ]
        progression = HistoricalWorkoutProgression()

        short = [
            item
            for item in reliable
            if item.pattern_type == "short_intervals"
            and item.work_distance_meters is not None
            and 325 <= item.work_distance_meters <= 475
            and 4 <= item.repetitions <= 12
        ]
        threshold = [
            item
            for item in reliable
            if item.pattern_type == "threshold_intervals"
            and item.work_distance_meters is not None
            and 800 <= item.work_distance_meters <= 1200
            and 3 <= item.repetitions <= 8
        ]
        long_specific = [
            item
            for item in reliable
            if item.pattern_type == "long_race_specific"
            and len(item.group_distances_meters) >= 2
            and all(
                2000 <= distance <= 5000
                for distance in item.group_distances_meters
            )
            and sum(item.group_distances_meters) <= 12000
        ]

        short_low = self._closest_repetitions(
            short,
            target=8,
        )
        short_high = self._maximum_repetitions(short)
        threshold_low = self._closest_repetitions(
            threshold,
            target=4,
        )
        threshold_high = self._maximum_repetitions(
            threshold
        )
        mixed = self._mixed(short, threshold)
        long_peak = (
            max(
                long_specific,
                key=lambda item: (
                    sum(item.group_distances_meters),
                    item.source_date,
                ),
            )
            if long_specific
            else None
        )

        if short_low is not None:
            progression.base.append(
                self._interval_prescription(short_low)
            )

        if threshold_low is not None:
            progression.development.append(
                self._interval_prescription(
                    threshold_low
                )
            )
        if short_high is not None:
            progression.development.append(
                self._interval_prescription(short_high)
            )

        if mixed is not None:
            short_item, threshold_item = mixed
            progression.specific.append(
                HistoricalWorkoutPrescription(
                    kind="mixed_intervals",
                    repetitions=min(
                        short_item.repetitions,
                        threshold_item.repetitions,
                    ),
                    threshold_distance_meters=(
                        threshold_item.work_distance_meters
                    ),
                    vo2_distance_meters=(
                        short_item.work_distance_meters
                    ),
                    source_activity_ids=[
                        short_item.source_activity_id
                    ],
                    reasons=[
                        (
                            "Séance mixte retrouvée dans une "
                            "préparation comparable réussie."
                        )
                    ],
                )
            )
        if threshold_high is not None:
            progression.specific.append(
                self._interval_prescription(
                    threshold_high
                )
            )
        if short_low is not None:
            progression.specific.append(
                self._interval_prescription(short_low)
            )
        if long_peak is not None:
            progression.specific.append(
                HistoricalWorkoutPrescription(
                    kind="long_race_specific",
                    group_distances_meters=list(
                        long_peak.group_distances_meters
                    ),
                    source_activity_ids=[
                        long_peak.source_activity_id
                    ],
                    reasons=list(long_peak.reasons),
                )
            )

        if not progression.available:
            progression.warnings.append(
                "Aucune progression historique comparable "
                "et réussie n'a pu être construite."
            )

        return progression

    @staticmethod
    def _closest_repetitions(
        patterns: list[HistoricalWorkoutPattern],
        *,
        target: int,
    ) -> HistoricalWorkoutPattern | None:
        if not patterns:
            return None
        return min(
            patterns,
            key=lambda item: (
                abs(item.repetitions - target),
                -item.confidence_score,
                item.source_date,
            ),
        )

    @staticmethod
    def _maximum_repetitions(
        patterns: list[HistoricalWorkoutPattern],
    ) -> HistoricalWorkoutPattern | None:
        if not patterns:
            return None
        return max(
            patterns,
            key=lambda item: (
                item.repetitions,
                item.confidence_score,
                item.source_date,
            ),
        )

    @staticmethod
    def _mixed(
        short: list[HistoricalWorkoutPattern],
        threshold: list[HistoricalWorkoutPattern],
    ) -> tuple[
        HistoricalWorkoutPattern,
        HistoricalWorkoutPattern,
    ] | None:
        threshold_by_activity = {
            item.source_activity_id: item
            for item in threshold
        }

        for short_item in short:
            threshold_item = threshold_by_activity.get(
                short_item.source_activity_id
            )
            if threshold_item is not None:
                return short_item, threshold_item

        return None

    @staticmethod
    def _interval_prescription(
        pattern: HistoricalWorkoutPattern,
    ) -> HistoricalWorkoutPrescription:
        return HistoricalWorkoutPrescription(
            kind=pattern.pattern_type,
            repetitions=pattern.repetitions,
            work_distance_meters=(
                pattern.work_distance_meters
            ),
            source_activity_ids=[
                pattern.source_activity_id
            ],
            reasons=list(pattern.reasons),
        )