"""
ATLAS OS
Analyse individualisée de la dérive cardiaque en endurance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Any

from .longitudinal_models import LongitudinalActivity


@dataclass(slots=True)
class CardiacDriftSegment:
    """Résumé d'une moitié stable de la séance."""

    duration_minutes: float
    sample_count: int
    average_speed_kmh: float
    average_heart_rate_bpm: float
    average_temperature_c: float | None
    aerobic_efficiency: float


@dataclass(slots=True)
class CardiacDriftAnalysis:
    """Évolution de la relation allure–fréquence cardiaque."""

    activity_id: str
    analyzable: bool = False
    warmup_excluded_minutes: float = 12.0
    valid_sample_count: int = 0
    excluded_hill_sample_count: int = 0
    first_segment: CardiacDriftSegment | None = None
    second_segment: CardiacDriftSegment | None = None
    heart_rate_change_bpm: float | None = None
    speed_change_percent: float | None = None
    aerobic_decoupling_percent: float | None = None
    drift_classification: str = "unknown"
    confidence_score: int = 0
    interpretation: list[str] = field(default_factory=list)
    planning_influences: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _StableSample:
    timestamp: datetime
    elapsed_seconds: float
    heart_rate_bpm: float
    speed_kmh: float
    temperature_c: float | None


class CardiacDriftAnalyzer:
    """
    Mesure le découplage entre charge externe et réponse cardiaque.

    L'échauffement, les arrêts et les pentes marquées sont écartés.
    La valeur doit ensuite être comparée à l'historique personnel.
    """

    DEFAULT_WARMUP_MINUTES = 12.0
    MINIMUM_ANALYSIS_MINUTES = 20.0
    MINIMUM_SAMPLE_COUNT = 120
    MAXIMUM_ABSOLUTE_GRADE_PERCENT = 3.0
    MINIMUM_RUNNING_SPEED_KMH = 6.0
    MAXIMUM_RUNNING_SPEED_KMH = 18.0

    def analyze(
        self,
        activity: LongitudinalActivity,
        *,
        warmup_minutes: float = DEFAULT_WARMUP_MINUTES,
    ) -> CardiacDriftAnalysis:
        """Analyse une activité détaillée de course."""
        result = CardiacDriftAnalysis(
            activity_id=activity.atlas_id,
            warmup_excluded_minutes=warmup_minutes,
        )

        if activity.activity_type not in {
            "running",
            "trail",
            "road_running",
        }:
            result.limitations.append(
                "Analyse réservée aux activités de course."
            )
            return result

        ordered = self._ordered_samples(activity.samples)
        if len(ordered) < 2:
            result.limitations.append(
                "Points FIT insuffisants."
            )
            return result

        stable, excluded_hills = self._stable_samples(
            ordered,
            warmup_minutes=warmup_minutes,
        )
        result.valid_sample_count = len(stable)
        result.excluded_hill_sample_count = excluded_hills

        if len(stable) < self.MINIMUM_SAMPLE_COUNT:
            result.limitations.append(
                "Échantillons stables insuffisants après filtrage."
            )
            return result

        stable_duration = (
            stable[-1].elapsed_seconds
            - stable[0].elapsed_seconds
        ) / 60.0
        if stable_duration < self.MINIMUM_ANALYSIS_MINUTES:
            result.limitations.append(
                "Durée stable insuffisante pour mesurer la dérive."
            )
            return result

        split_elapsed = (
            stable[0].elapsed_seconds
            + stable[-1].elapsed_seconds
        ) / 2.0
        first_values = [
            item
            for item in stable
            if item.elapsed_seconds <= split_elapsed
        ]
        second_values = [
            item
            for item in stable
            if item.elapsed_seconds > split_elapsed
        ]

        if (
            len(first_values) < 30
            or len(second_values) < 30
        ):
            result.limitations.append(
                "Répartition temporelle insuffisante."
            )
            return result

        first = self._segment(first_values)
        second = self._segment(second_values)
        result.first_segment = first
        result.second_segment = second

        result.heart_rate_change_bpm = round(
            second.average_heart_rate_bpm
            - first.average_heart_rate_bpm,
            1,
        )
        result.speed_change_percent = round(
            (
                second.average_speed_kmh
                / first.average_speed_kmh
                - 1.0
            )
            * 100.0,
            1,
        )
        result.aerobic_decoupling_percent = round(
            (
                first.aerobic_efficiency
                - second.aerobic_efficiency
            )
            / first.aerobic_efficiency
            * 100.0,
            1,
        )
        result.drift_classification = self._classification(
            result.aerobic_decoupling_percent
        )
        result.confidence_score = self._confidence(
            stable=stable,
            original_count=len(ordered),
            stable_duration_minutes=stable_duration,
            first=first,
            second=second,
        )
        result.analyzable = True

        self._interpret(result)
        return result

    def _stable_samples(
        self,
        samples: list[Any],
        *,
        warmup_minutes: float,
    ) -> tuple[list[_StableSample], int]:
        first_time = self._timestamp(samples[0])
        stable: list[_StableSample] = []
        excluded_hills = 0
        for index, sample in enumerate(samples):
            timestamp = self._timestamp(sample)
            heart_rate = self._number(
                getattr(sample, "heart_rate_bpm", None)
            )
            speed_mps = self._number(
                getattr(sample, "speed_mps", None)
            )

            if (
                timestamp is None
                or first_time is None
                or heart_rate is None
                or speed_mps is None
            ):
                continue

            elapsed = (
                timestamp - first_time
            ).total_seconds()
            speed_kmh = speed_mps * 3.6

            if elapsed < warmup_minutes * 60:
                continue
            if not (
                self.MINIMUM_RUNNING_SPEED_KMH
                <= speed_kmh
                <= self.MAXIMUM_RUNNING_SPEED_KMH
            ):
                continue

            grade_reference = (
                samples[index - 10]
                if index >= 10
                else None
            )
            grade = self._grade_percent(
                grade_reference,
                sample,
            )

            if (
                grade is not None
                and abs(grade)
                > self.MAXIMUM_ABSOLUTE_GRADE_PERCENT
            ):
                excluded_hills += 1
                continue

            stable.append(
                _StableSample(
                    timestamp=timestamp,
                    elapsed_seconds=elapsed,
                    heart_rate_bpm=heart_rate,
                    speed_kmh=speed_kmh,
                    temperature_c=self._number(
                        getattr(sample, "temperature_c", None)
                    ),
                )
            )

        return stable, excluded_hills

    def _grade_percent(
        self,
        previous: Any,
        current: Any,
    ) -> float | None:
        if previous is None:
            return None

        previous_distance = self._number(
            getattr(previous, "distance_meters", None)
        )
        current_distance = self._number(
            getattr(current, "distance_meters", None)
        )
        previous_altitude = self._number(
            getattr(previous, "altitude_m", None)
        )
        current_altitude = self._number(
            getattr(current, "altitude_m", None)
        )

        if None in {
            previous_distance,
            current_distance,
            previous_altitude,
            current_altitude,
        }:
            return None

        distance_change = (
            current_distance - previous_distance
        )
        if distance_change < 2.0:
            return None

        return (
            (current_altitude - previous_altitude)
            / distance_change
            * 100.0
        )

    @staticmethod
    def _segment(
        values: list[_StableSample],
    ) -> CardiacDriftSegment:
        average_speed = mean(
            item.speed_kmh for item in values
        )
        average_heart_rate = mean(
            item.heart_rate_bpm for item in values
        )
        temperatures = [
            item.temperature_c
            for item in values
            if item.temperature_c is not None
        ]

        return CardiacDriftSegment(
            duration_minutes=round(
                (
                    values[-1].elapsed_seconds
                    - values[0].elapsed_seconds
                )
                / 60.0,
                1,
            ),
            sample_count=len(values),
            average_speed_kmh=round(average_speed, 2),
            average_heart_rate_bpm=round(
                average_heart_rate,
                1,
            ),
            average_temperature_c=(
                round(mean(temperatures), 1)
                if temperatures
                else None
            ),
            aerobic_efficiency=round(
                average_speed / average_heart_rate,
                5,
            ),
        )

    @staticmethod
    def _classification(decoupling: float) -> str:
        if decoupling <= 3.0:
            return "low"
        if decoupling <= 5.0:
            return "controlled"
        if decoupling <= 8.0:
            return "notable"
        return "high"

    @staticmethod
    def _confidence(
        *,
        stable: list[_StableSample],
        original_count: int,
        stable_duration_minutes: float,
        first: CardiacDriftSegment,
        second: CardiacDriftSegment,
    ) -> int:
        coverage = (
            len(stable) / original_count
            if original_count
            else 0.0
        )
        score = 45.0
        score += min(20.0, stable_duration_minutes / 2.0)
        score += min(20.0, coverage * 25.0)
        score += min(
            10.0,
            min(first.sample_count, second.sample_count) / 30.0,
        )
        if (
            first.average_temperature_c is not None
            and second.average_temperature_c is not None
        ):
            score += 5.0
        return round(max(0.0, min(100.0, score)))

    @staticmethod
    def _interpret(
        result: CardiacDriftAnalysis,
    ) -> None:
        decoupling = result.aerobic_decoupling_percent
        heart_rate_change = result.heart_rate_change_bpm

        result.interpretation.append(
            "Échauffement exclu : "
            f"{result.warmup_excluded_minutes:.0f} minutes."
        )
        result.interpretation.append(
            "Évolution cardiaque sur les portions stables : "
            f"{heart_rate_change:+.1f} bpm."
        )
        result.interpretation.append(
            "Découplage aérobie initial : "
            f"{decoupling:.1f} % ({result.drift_classification})."
        )

        if result.excluded_hill_sample_count:
            result.interpretation.append(
                f"{result.excluded_hill_sample_count} point(s) "
                "de pente marquée exclus."
            )

        if result.drift_classification in {"low", "controlled"}:
            result.planning_influences.append(
                "Endurance aérobie correctement maîtrisée."
            )
        elif result.drift_classification == "notable":
            result.planning_influences.append(
                "Maintenir la Z2 et développer progressivement "
                "la durée des sorties longues."
            )
        else:
            result.planning_influences.append(
                "Réévaluer récupération, chaleur, hydratation "
                "et intensité avant d'augmenter le volume."
            )

        result.limitations.append(
            "Interprétation à confirmer par plusieurs séances "
            "comparables et par la référence personnelle."
        )

    @staticmethod
    def _ordered_samples(samples: list[Any]) -> list[Any]:
        return sorted(
            [
                item
                for item in samples
                if CardiacDriftAnalyzer._timestamp(item)
                is not None
            ],
            key=CardiacDriftAnalyzer._timestamp,
        )

    @staticmethod
    def _timestamp(sample: Any) -> datetime | None:
        value = getattr(sample, "timestamp", None)
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError:
            return None

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None