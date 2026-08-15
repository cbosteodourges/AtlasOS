"""
ATLAS OS
Estimation longitudinale et explicable des références cardiaques.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from statistics import median
from typing import Iterable, Optional

from .longitudinal_models import LongitudinalActivity


@dataclass(slots=True)
class AnnualHeartRatePeak:
    """Pic cardiaque individuel retenu pour une année."""

    year: int
    heart_rate_bpm: int
    activity_id: str
    recorded_at: datetime

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class HeartRateReferenceAnalysis:
    """Référence de FC max issue des données et de la théorie."""

    maximum_heart_rate_bpm: Optional[int]
    observed_peak_bpm: Optional[int]
    theoretical_220_minus_age_bpm: Optional[float]
    theoretical_210_minus_065_age_bpm: Optional[float]
    confidence_score: int
    source: str
    accepted_observation_count: int
    rejected_activity_ids: list[str] = field(default_factory=list)
    annual_peaks: list[AnnualHeartRatePeak] = field(
        default_factory=list
    )
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["annual_peaks"] = [
            peak.to_dict()
            for peak in self.annual_peaks
        ]
        return result


class HeartRateReferenceAnalyzer:
    """Déduit la FC max sans confondre un pic isolé avec une preuve."""

    MINIMUM_HEART_RATE_BPM = 80
    MAXIMUM_HEART_RATE_BPM = 230
    MINIMUM_DURATION_MINUTES = 5
    MINIMUM_QUALITY_SCORE = 50
    EXCEPTION_MARGIN_BPM = 8
    CORROBORATION_DISTANCE_BPM = 3

    def analyze(
        self,
        activities: Iterable[LongitudinalActivity],
        *,
        age_years: Optional[int] = None,
    ) -> HeartRateReferenceAnalysis:
        theoretical_220 = (
            220.0 - age_years
            if age_years is not None
            else None
        )
        theoretical_210 = (
            210.0 - 0.65 * age_years
            if age_years is not None
            else None
        )

        candidates = [
            activity
            for activity in activities
            if self._eligible(activity)
        ]
        accepted: list[LongitudinalActivity] = []
        rejected: list[LongitudinalActivity] = []

        theoretical_ceiling = (
            min(theoretical_220, theoretical_210)
            if (
                theoretical_220 is not None
                and theoretical_210 is not None
            )
            else None
        )

        for activity in candidates:
            value = float(activity.maximum_heart_rate_bpm)
            exceptional = (
                theoretical_ceiling is not None
                and value
                > theoretical_ceiling + self.EXCEPTION_MARGIN_BPM
            )
            corroborated = self._corroborated(
                activity,
                candidates,
            )

            if exceptional and not corroborated:
                rejected.append(activity)
            else:
                accepted.append(activity)

        annual_peaks = self._annual_peaks(accepted)
        observed_peak = (
            max(
                int(round(activity.maximum_heart_rate_bpm))
                for activity in accepted
            )
            if accepted
            else None
        )
        current_reference = self._current_reference(
            annual_peaks,
            theoretical_220,
        )

        if current_reference is not None:
            maximum_heart_rate = current_reference
            source = "longitudinal"
        elif theoretical_220 is not None and theoretical_210 is not None:
            maximum_heart_rate = round(
                median([theoretical_220, theoretical_210])
            )
            source = "theoretical_prior"
        else:
            maximum_heart_rate = None
            source = "insufficient_data"

        confidence = self._confidence(
            accepted,
            annual_peaks,
            rejected,
            source,
        )
        explanations = self._explanations(
            maximum_heart_rate,
            annual_peaks,
            rejected,
            theoretical_220,
            theoretical_210,
            source,
        )

        return HeartRateReferenceAnalysis(
            maximum_heart_rate_bpm=maximum_heart_rate,
            observed_peak_bpm=observed_peak,
            theoretical_220_minus_age_bpm=theoretical_220,
            theoretical_210_minus_065_age_bpm=theoretical_210,
            confidence_score=confidence,
            source=source,
            accepted_observation_count=len(accepted),
            rejected_activity_ids=[
                activity.atlas_id
                for activity in rejected
            ],
            annual_peaks=annual_peaks,
            explanations=explanations,
        )

    def _eligible(
        self,
        activity: LongitudinalActivity,
    ) -> bool:
        value = activity.maximum_heart_rate_bpm
        if value is None:
            return False

        activity_type = activity.activity_type.lower()

        return all([
            value is not None,
            self.MINIMUM_HEART_RATE_BPM
            <= float(value)
            <= self.MAXIMUM_HEART_RATE_BPM,
            activity.duration_minutes
            >= self.MINIMUM_DURATION_MINUTES,
            (
                activity.data_quality_score == 0
                or activity.data_quality_score
                >= self.MINIMUM_QUALITY_SCORE
            ),
            any(
                token in activity_type
                for token in ("run", "running", "course")
            ),
        ])

    def _corroborated(
        self,
        activity: LongitudinalActivity,
        candidates: list[LongitudinalActivity],
    ) -> bool:
        value = float(activity.maximum_heart_rate_bpm)

        return any(
            other.atlas_id != activity.atlas_id
            and abs(
                float(other.maximum_heart_rate_bpm) - value
            ) <= self.CORROBORATION_DISTANCE_BPM
            for other in candidates
        )

    @staticmethod
    def _annual_peaks(
        activities: list[LongitudinalActivity],
    ) -> list[AnnualHeartRatePeak]:
        peaks: dict[int, LongitudinalActivity] = {}

        for activity in activities:
            year = activity.start_time.year
            current = peaks.get(year)
            if (
                current is None
                or float(activity.maximum_heart_rate_bpm)
                > float(current.maximum_heart_rate_bpm)
            ):
                peaks[year] = activity

        return [
            AnnualHeartRatePeak(
                year=year,
                heart_rate_bpm=int(round(
                    activity.maximum_heart_rate_bpm
                )),
                activity_id=activity.atlas_id,
                recorded_at=activity.start_time,
            )
            for year, activity in sorted(peaks.items())
        ]

    @staticmethod
    def _current_reference(
        annual_peaks: list[AnnualHeartRatePeak],
        theoretical_220: Optional[float],
    ) -> Optional[int]:
        if not annual_peaks:
            return None

        latest_year = max(
            peak.year
            for peak in annual_peaks
        )
        latest = next(
            peak
            for peak in annual_peaks
            if peak.year == latest_year
        )
        if theoretical_220 is None:
            return latest.heart_rate_bpm

        return min(
            latest.heart_rate_bpm,
            round(theoretical_220),
        )

    @staticmethod
    def _confidence(
        accepted: list[LongitudinalActivity],
        annual_peaks: list[AnnualHeartRatePeak],
        rejected: list[LongitudinalActivity],
        source: str,
    ) -> int:
        if source == "insufficient_data":
            return 0
        if source == "theoretical_prior":
            return 25

        score = 35
        score += min(len(accepted), 20) * 2
        score += min(len(annual_peaks), 4) * 6
        if rejected:
            score += 5
        return min(score, 95)

    @staticmethod
    def _explanations(
        maximum_heart_rate: Optional[int],
        annual_peaks: list[AnnualHeartRatePeak],
        rejected: list[LongitudinalActivity],
        theoretical_220: Optional[float],
        theoretical_210: Optional[float],
        source: str,
    ) -> list[str]:
        explanations: list[str] = []

        if source == "longitudinal":
            explanations.append(
                "La FC max est issue du pic annuel le plus récent "
                "et cohérent avec l'historique individuel."
            )
        elif source == "theoretical_prior":
            explanations.append(
                "Faute d'historique suffisant, Atlas utilise "
                "provisoirement la moyenne de deux repères théoriques."
            )

        if theoretical_220 is not None:
            explanations.append(
                f"Repère 220 - âge : {theoretical_220:.0f} bpm."
            )
        if theoretical_210 is not None:
            explanations.append(
                "Repère 210 - 0,65 × âge : "
                f"{theoretical_210:.1f} bpm."
            )
        if annual_peaks:
            history = ", ".join(
                f"{peak.year}: {peak.heart_rate_bpm}"
                for peak in annual_peaks
            )
            explanations.append(
                f"Pics annuels retenus : {history} bpm."
            )
        if rejected:
            explanations.append(
                f"{len(rejected)} mesure(s) isolée(s) ont été "
                "écartées comme anomalies d'identité possibles."
            )
        if maximum_heart_rate is not None:
            explanations.append(
                f"Référence cardiaque Atlas : "
                f"{maximum_heart_rate} bpm."
            )

        return explanations
