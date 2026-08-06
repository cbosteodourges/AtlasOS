"""
ATLAS OS
Évolution longitudinale des seuils physiologiques.
"""

from copy import deepcopy
from datetime import datetime
from statistics import mean
from typing import List, Optional

from .athlete_profile import (
    AthleteProfile,
    EvolvingThreshold,
    ThresholdHistoryEntry,
)
from .session_fingerprint import (
    DetailedSessionAnalysis,
    ThresholdObservation,
)


class ThresholdEvolutionAnalyzer:
    """
    Consolide les observations SV1 et SV2 de plusieurs séances.

    Une observation isolée ne modifie jamais le profil.
    """

    MINIMUM_OBSERVATION_COUNT = 3
    MINIMUM_OBSERVATION_CONFIDENCE = 60
    MAXIMUM_UPDATE_PERCENT = 3.0

    def update(
        self,
        profile: AthleteProfile,
        analyses: List[DetailedSessionAnalysis],
        updated_at: Optional[datetime] = None,
    ) -> AthleteProfile:
        """Retourne une copie du profil avec les seuils actualisés."""
        result = deepcopy(profile)
        update_time = (
            updated_at
            or datetime.now().astimezone()
        )

        sv1_observations = self._observations(
            analyses,
            "sv1",
        )
        sv2_observations = self._observations(
            analyses,
            "sv2",
        )

        result.physiological.sv1 = self._update_threshold(
            current=result.physiological.sv1,
            observations=sv1_observations,
            updated_at=update_time,
        )
        result.physiological.sv2 = self._update_threshold(
            current=result.physiological.sv2,
            observations=sv2_observations,
            updated_at=update_time,
            seed_speed_kmh=(
                result.physiological
                .threshold_speed_kmh
            ),
            seed_heart_rate_bpm=(
                result.physiological
                .threshold_heart_rate_bpm
            ),
        )

        if result.physiological.sv2.speed_kmh is not None:
            result.physiological.threshold_speed_kmh = (
                result.physiological.sv2.speed_kmh
            )

        if (
            result.physiological.sv2.heart_rate_bpm
            is not None
        ):
            result.physiological.threshold_heart_rate_bpm = (
                result.physiological.sv2.heart_rate_bpm
            )

        return result

    def _update_threshold(
        self,
        current: EvolvingThreshold,
        observations: List[ThresholdObservation],
        updated_at: datetime,
        seed_speed_kmh: Optional[float] = None,
        seed_heart_rate_bpm: Optional[float] = None,
    ) -> EvolvingThreshold:
        if (
            len(observations)
            < self.MINIMUM_OBSERVATION_COUNT
        ):
            return current

        speeds = [
            observation.estimated_speed_kmh
            for observation in observations
            if observation.estimated_speed_kmh
            is not None
        ]
        heart_rates = [
            observation.estimated_heart_rate_bpm
            for observation in observations
            if observation.estimated_heart_rate_bpm
            is not None
        ]

        speed = self._weighted_average(
            observations,
            "estimated_speed_kmh",
        )
        heart_rate = self._weighted_average(
            observations,
            "estimated_heart_rate_bpm",
        )

        previous_speed = (
            current.speed_kmh
            if current.speed_kmh is not None
            else seed_speed_kmh
        )
        previous_heart_rate = (
            current.heart_rate_bpm
            if current.heart_rate_bpm is not None
            else seed_heart_rate_bpm
        )

        speed = self._limited_update(
            previous_speed,
            speed,
        )
        heart_rate = self._limited_update(
            previous_heart_rate,
            heart_rate,
        )

        confidence = self._confidence_score(
            observations,
            speeds,
            heart_rates,
        )
        trend = self._trend(
            previous_speed,
            speed,
        )

        evidence = []
        for observation in observations:
            for item in observation.evidence:
                if item not in evidence:
                    evidence.append(item)

        history = list(current.history)
        history.append(
            ThresholdHistoryEntry(
                recorded_at=updated_at,
                speed_kmh=speed,
                heart_rate_bpm=heart_rate,
                confidence_score=confidence,
                observation_count=len(observations),
            )
        )

        return EvolvingThreshold(
            threshold_name=current.threshold_name,
            speed_kmh=speed,
            heart_rate_bpm=heart_rate,
            minimum_speed_kmh=(
                min(speeds) if speeds else None
            ),
            maximum_speed_kmh=(
                max(speeds) if speeds else None
            ),
            minimum_heart_rate_bpm=(
                min(heart_rates)
                if heart_rates
                else None
            ),
            maximum_heart_rate_bpm=(
                max(heart_rates)
                if heart_rates
                else None
            ),
            confidence_score=confidence,
            observation_count=len(observations),
            trend=trend,
            last_updated_at=updated_at,
            evidence=evidence,
            history=history,
        )

    def _observations(
        self,
        analyses: List[DetailedSessionAnalysis],
        threshold_name: str,
    ) -> List[ThresholdObservation]:
        selected = []

        for analysis in analyses:
            for observation in (
                analysis.threshold_observations
            ):
                if (
                    observation.threshold_name
                    == threshold_name
                    and observation.confidence_score
                    >= self.MINIMUM_OBSERVATION_CONFIDENCE
                ):
                    selected.append(observation)

        return selected

    @staticmethod
    def _weighted_average(
        observations: List[ThresholdObservation],
        field_name: str,
    ) -> Optional[float]:
        weighted_total = 0.0
        total_weight = 0.0

        for observation in observations:
            value = getattr(observation, field_name)

            if value is None:
                continue

            weight = max(
                1,
                observation.confidence_score,
            )
            weighted_total += value * weight
            total_weight += weight

        if total_weight <= 0:
            return None

        return weighted_total / total_weight

    def _limited_update(
        self,
        previous: Optional[float],
        proposed: Optional[float],
    ) -> Optional[float]:
        if proposed is None:
            return previous

        if previous is None or previous <= 0:
            return proposed

        maximum_change = (
            previous
            * self.MAXIMUM_UPDATE_PERCENT
            / 100
        )
        lower = previous - maximum_change
        upper = previous + maximum_change

        return min(
            upper,
            max(lower, proposed),
        )

    @staticmethod
    def _confidence_score(
        observations: List[ThresholdObservation],
        speeds: List[float],
        heart_rates: List[float],
    ) -> int:
        base = mean(
            observation.confidence_score
            for observation in observations
        )

        agreement_penalty = 0.0

        if speeds:
            speed_spread = max(speeds) - min(speeds)
            agreement_penalty += min(
                15,
                speed_spread * 10,
            )

        if heart_rates:
            heart_rate_spread = (
                max(heart_rates)
                - min(heart_rates)
            )
            agreement_penalty += min(
                15,
                heart_rate_spread,
            )

        repeated_evidence_bonus = min(
            12,
            len(observations) * 2,
        )

        return max(
            0,
            min(
                95,
                round(
                    base
                    - agreement_penalty
                    + repeated_evidence_bonus
                ),
            ),
        )

    @staticmethod
    def _trend(
        previous_speed: Optional[float],
        current_speed: Optional[float],
    ) -> str:
        if (
            previous_speed is None
            or current_speed is None
        ):
            return "baseline"

        difference_percent = (
            current_speed - previous_speed
        ) / previous_speed * 100

        if difference_percent > 1:
            return "improving"

        if difference_percent < -1:
            return "declining"

        return "stable"