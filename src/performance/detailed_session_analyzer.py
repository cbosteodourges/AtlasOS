"""
ATLAS OS
Analyse détaillée des points, tours et zones d'une séance FIT.
"""

from datetime import datetime
from statistics import mean
from typing import List, Optional, Tuple

from src.connectors import ActivitySample

from .athlete_profile import AthleteProfile
from .longitudinal_models import LongitudinalActivity
from .session_fingerprint import (
    DetailedSessionAnalysis,
    SessionBlock,
    ThresholdObservation,
)
from .zones import TrainingZonesEngine


class DetailedSessionAnalyzer:
    """Détecte et interprète les blocs d'une séance détaillée."""

    ACCELERATION_THRESHOLD_MPS2 = 0.045

    def analyze(
        self,
        activity: LongitudinalActivity,
        profile: Optional[AthleteProfile] = None,
    ) -> DetailedSessionAnalysis:
        """Analyse les points FIT d'une activité."""
        samples = self._ordered_samples(
            activity.samples
        )

        if len(samples) < 2:
            return DetailedSessionAnalysis(
                activity_id=activity.atlas_id,
                interpretation=[
                    "Points FIT insuffisants pour détecter "
                    "les blocs de la séance."
                ],
            )

        vma_kmh = self._vma(profile)
        threshold_speed_kmh = self._threshold_speed(
            profile
        )
        intervals = self._build_intervals(
            samples,
            vma_kmh,
            threshold_speed_kmh,
        )
        blocks = self._group_intervals(intervals)

        work_blocks = [
            block
            for block in blocks
            if block.block_type
            not in {"recovery", "warm_up", "cool_down"}
        ]
        recovery_blocks = [
            block
            for block in blocks
            if block.block_type == "recovery"
        ]

        physiological_load = min(
            100,
            round(
                sum(
                    block.physiological_load_score
                    for block in blocks
                )
            ),
        )
        biomechanical_load = min(
            100,
            round(
                sum(
                    block.biomechanical_load_score
                    for block in blocks
                )
            ),
        )

        confidence = self._confidence_score(
            samples,
            vma_kmh,
            activity,
        )
        dominant_work_type = self._dominant_type(
            work_blocks
        )

        return DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=blocks,
            threshold_observations=(
                self._threshold_observations(blocks)
            ),
            dominant_work_type=dominant_work_type,
            work_duration_seconds=sum(
                block.duration_seconds
                for block in work_blocks
            ),
            recovery_duration_seconds=sum(
                block.duration_seconds
                for block in recovery_blocks
            ),
            work_distance_meters=sum(
                block.distance_meters
                for block in work_blocks
            ),
            recovery_distance_meters=sum(
                block.distance_meters
                for block in recovery_blocks
            ),
            physiological_load_score=(
                physiological_load
            ),
            biomechanical_load_score=(
                biomechanical_load
            ),
            analysis_confidence_score=confidence,
            interpretation=self._interpretation(
                blocks,
                dominant_work_type,
            ),
            planning_influences=(
                self._planning_influences(
                    blocks,
                    physiological_load,
                    biomechanical_load,
                )
            ),
        )

    def _threshold_observations(
        self,
        blocks: List[SessionBlock],
    ) -> List[ThresholdObservation]:
        """Repère les transitions compatibles avec SV1 et SV2."""
        observations = {}

        for left, right in zip(blocks, blocks[1:]):
            observation = None

            if (
                left.block_type == "z2"
                and right.block_type == "z3"
            ):
                observation = self._threshold_observation(
                    "sv1",
                    left,
                    right,
                    (
                        "Transition stable entre endurance "
                        "fondamentale et tempo."
                    ),
                )

            elif (
                left.block_type == "z3"
                and right.block_type == "sv2"
            ):
                observation = self._threshold_observation(
                    "sv2",
                    left,
                    right,
                    (
                        "Transition stable entre tempo "
                        "et travail au second seuil."
                    ),
                    use_right_block=True,
                )

            if observation is None:
                continue

            previous = observations.get(
                observation.threshold_name
            )

            if (
                previous is None
                or observation.confidence_score
                > previous.confidence_score
            ):
                observations[
                    observation.threshold_name
                ] = observation

        return [
            observations[name]
            for name in ("sv1", "sv2")
            if name in observations
        ]

    @staticmethod
    def _threshold_observation(
        threshold_name: str,
        left: SessionBlock,
        right: SessionBlock,
        evidence: str,
        use_right_block: bool = False,
    ) -> ThresholdObservation:
        speeds = [
            value
            for value in (
                left.average_speed_kmh,
                right.average_speed_kmh,
            )
            if value is not None
        ]
        heart_rates = [
            value
            for value in (
                left.average_heart_rate_bpm,
                right.average_heart_rate_bpm,
            )
            if value is not None
        ]

        if use_right_block:
            estimated_speed = right.average_speed_kmh
            estimated_heart_rate = (
                right.average_heart_rate_bpm
            )
        else:
            estimated_speed = (
                mean(speeds) if speeds else None
            )
            estimated_heart_rate = (
                mean(heart_rates)
                if heart_rates
                else None
            )

        stable_duration = min(
            left.duration_seconds,
            right.duration_seconds,
        )
        confidence = 45
        confidence += min(
            30,
            round(stable_duration / 12),
        )
        confidence += 10 if estimated_speed else 0
        confidence += 10 if estimated_heart_rate else 0

        return ThresholdObservation(
            threshold_name=threshold_name,
            estimated_speed_kmh=estimated_speed,
            estimated_heart_rate_bpm=(
                estimated_heart_rate
            ),
            confidence_score=min(95, confidence),
            evidence=[
                evidence,
                (
                    "Observation issue d'une seule séance : "
                    "confirmation longitudinale nécessaire."
                ),
            ],
        )

    def _build_intervals(
        self,
        samples: List[ActivitySample],
        vma_kmh: Optional[float],
        threshold_speed_kmh: Optional[float],
    ) -> List[Tuple[str, ActivitySample, float, float, float]]:
        intervals = []

        for index in range(len(samples) - 1):
            current = samples[index]
            following = samples[index + 1]
            start = self._date(current.timestamp)
            end = self._date(following.timestamp)
            duration = max(
                0.0,
                (end - start).total_seconds(),
            )

            if duration <= 0:
                continue

            speed = current.speed_mps or 0.0
            previous_speed = (
                samples[index - 1].speed_mps
                if index > 0
                else None
            )
            acceleration = self._acceleration(
                previous_speed,
                speed,
                duration,
            )
            block_type = self._block_type(
                speed * 3.6,
                acceleration,
                vma_kmh,
                threshold_speed_kmh,
            )
            distance = self._interval_distance(
                current,
                following,
                speed,
                duration,
            )

            intervals.append(
                (
                    block_type,
                    current,
                    duration,
                    distance,
                    acceleration,
                )
            )

        return intervals

    def _group_intervals(
        self,
        intervals: List[
            Tuple[str, ActivitySample, float, float, float]
        ],
    ) -> List[SessionBlock]:
        if not intervals:
            return []

        groups = []
        current_group = [intervals[0]]

        for interval in intervals[1:]:
            if interval[0] == current_group[-1][0]:
                current_group.append(interval)
            else:
                groups.append(current_group)
                current_group = [interval]

        groups.append(current_group)

        first_time = self._date(
            intervals[0][1].timestamp
        )

        return [
            self._build_block(
                index,
                group,
                first_time,
            )
            for index, group in enumerate(groups, start=1)
        ]

    def _build_block(
        self,
        index: int,
        group: List[
            Tuple[str, ActivitySample, float, float, float]
        ],
        first_time: datetime,
    ) -> SessionBlock:
        samples = [interval[1] for interval in group]
        duration = sum(
            interval[2] for interval in group
        )
        distance = sum(
            interval[3] for interval in group
        )
        start_time = self._date(samples[0].timestamp)
        end_offset = (
            start_time - first_time
        ).total_seconds() + duration
        block_type = group[0][0]

        speeds = [
            sample.speed_mps * 3.6
            for sample in samples
            if sample.speed_mps is not None
        ]

        return SessionBlock(
            block_index=index,
            block_type=block_type,
            start_offset_seconds=(
                start_time - first_time
            ).total_seconds(),
            end_offset_seconds=end_offset,
            duration_seconds=duration,
            distance_meters=distance,
            average_speed_kmh=self._average(speeds),
            maximum_speed_kmh=(
                max(speeds) if speeds else None
            ),
            average_heart_rate_bpm=self._sample_average(
                samples,
                "heart_rate_bpm",
            ),
            maximum_heart_rate_bpm=self._sample_maximum(
                samples,
                "heart_rate_bpm",
            ),
            average_power_watts=self._sample_average(
                samples,
                "power_watts",
            ),
            average_cadence_spm=self._sample_average(
                samples,
                "cadence_spm",
            ),
            average_stride_length_m=self._sample_average(
                samples,
                "stride_length_m",
            ),
            average_vertical_ratio_percent=(
                self._sample_average(
                    samples,
                    "vertical_ratio_percent",
                )
            ),
            average_vertical_oscillation_cm=(
                self._sample_average(
                    samples,
                    "vertical_oscillation_cm",
                )
            ),
            average_ground_contact_time_ms=(
                self._sample_average(
                    samples,
                    "ground_contact_time_ms",
                )
            ),
            physiological_load_score=(
                self._physiological_load(
                    block_type,
                    duration,
                )
            ),
            biomechanical_load_score=(
                self._biomechanical_load(
                    block_type,
                    duration,
                    samples,
                )
            ),
            confidence_score=self._block_confidence(
                samples
            ),
            detection_reasons=[
                self._detection_reason(block_type)
            ],
        )

    def _block_type(
        self,
        speed_kmh: float,
        acceleration_mps2: float,
        vma_kmh: Optional[float],
        threshold_speed_kmh: Optional[float],
    ) -> str:
        if (
            acceleration_mps2
            >= self.ACCELERATION_THRESHOLD_MPS2
            and speed_kmh > 0
        ):
            return "acceleration"

        if not vma_kmh or vma_kmh <= 0:
            return "unknown"

        vma_percent = speed_kmh / vma_kmh * 100

        if vma_percent < 65:
            return "recovery"
        if vma_percent < 75:
            return "z2"
        if vma_percent < 85:
            return "z3"

        if (
            threshold_speed_kmh
            and speed_kmh
            >= threshold_speed_kmh * 0.96
            and speed_kmh
            <= threshold_speed_kmh * 1.04
        ):
            return "sv2"

        if vma_percent < 95:
            return "sv2"
        if vma_percent <= 105:
            return "vma"

        return "sprint"

    @staticmethod
    def _acceleration(
        previous_speed: Optional[float],
        current_speed: float,
        duration_seconds: float,
    ) -> float:
        if previous_speed is None or duration_seconds <= 0:
            return 0.0

        return (
            current_speed - previous_speed
        ) / duration_seconds

    @staticmethod
    def _interval_distance(
        current: ActivitySample,
        following: ActivitySample,
        speed_mps: float,
        duration_seconds: float,
    ) -> float:
        if (
            current.distance_meters is not None
            and following.distance_meters is not None
        ):
            return max(
                0.0,
                following.distance_meters
                - current.distance_meters,
            )

        return max(
            0.0,
            speed_mps * duration_seconds,
        )

    @staticmethod
    def _physiological_load(
        block_type: str,
        duration_seconds: float,
    ) -> int:
        intensity = {
            "recovery": 0.5,
            "z2": 1.0,
            "z3": 1.5,
            "sv2": 2.2,
            "vma": 3.0,
            "acceleration": 3.2,
            "sprint": 3.8,
            "unknown": 0.7,
        }.get(block_type, 0.7)

        return max(
            0,
            round(duration_seconds / 60 * intensity),
        )

    @staticmethod
    def _biomechanical_load(
        block_type: str,
        duration_seconds: float,
        samples: List[ActivitySample],
    ) -> int:
        intensity = {
            "recovery": 0.4,
            "z2": 0.8,
            "z3": 1.2,
            "sv2": 1.7,
            "vma": 2.4,
            "acceleration": 2.8,
            "sprint": 3.5,
            "unknown": 0.6,
        }.get(block_type, 0.6)

        available_dynamics = sum(
            1
            for name in (
                "cadence_spm",
                "ground_contact_time_ms",
                "vertical_ratio_percent",
                "stride_length_m",
            )
            if any(
                getattr(sample, name) is not None
                for sample in samples
            )
        )
        dynamics_factor = 1 + available_dynamics * 0.05

        return max(
            0,
            round(
                duration_seconds
                / 60
                * intensity
                * dynamics_factor
            ),
        )

    @staticmethod
    def _block_confidence(
        samples: List[ActivitySample],
    ) -> int:
        available = 0

        for name in (
            "speed_mps",
            "heart_rate_bpm",
            "distance_meters",
            "cadence_spm",
            "power_watts",
        ):
            if any(
                getattr(sample, name) is not None
                for sample in samples
            ):
                available += 1

        return min(100, 45 + available * 10)

    @staticmethod
    def _confidence_score(
        samples: List[ActivitySample],
        vma_kmh: Optional[float],
        activity: LongitudinalActivity,
    ) -> int:
        score = 35
        score += min(25, len(samples) // 100)
        score += 20 if vma_kmh else 0
        score += 10 if activity.laps else 0
        score += 10 if activity.time_in_zones else 0

        return min(100, score)

    @staticmethod
    def _dominant_type(
        blocks: List[SessionBlock],
    ) -> str:
        if not blocks:
            return "unknown"

        durations = {}

        for block in blocks:
            durations[block.block_type] = (
                durations.get(block.block_type, 0.0)
                + block.duration_seconds
            )

        return max(durations, key=durations.get)

    @staticmethod
    def _interpretation(
        blocks: List[SessionBlock],
        dominant_work_type: str,
    ) -> List[str]:
        if not blocks:
            return [
                "Aucun bloc exploitable n'a été détecté."
            ]

        return [
            f"{len(blocks)} blocs homogènes détectés.",
            (
                "Travail dominant détecté : "
                f"{dominant_work_type}."
            ),
        ]

    @staticmethod
    def _planning_influences(
        blocks: List[SessionBlock],
        physiological_load: int,
        biomechanical_load: int,
    ) -> List[str]:
        influences = []

        if any(
            block.block_type
            in {"vma", "sprint", "acceleration"}
            for block in blocks
        ):
            influences.append(
                "Prévoir une récupération suffisante avant "
                "le prochain travail de haute intensité."
            )

        if biomechanical_load > physiological_load:
            influences.append(
                "Surveiller la récupération biomécanique "
                "avant la prochaine séance rapide."
            )

        if not influences:
            influences.append(
                "Utiliser cette séance pour ajuster "
                "progressivement les prochaines allures."
            )

        return influences

    @staticmethod
    def _detection_reason(
        block_type: str,
    ) -> str:
        labels = {
            "recovery": "Vitesse inférieure à 65 % de la VMA.",
            "z2": "Vitesse comprise entre 65 et 75 % de la VMA.",
            "z3": "Vitesse comprise entre 75 et 85 % de la VMA.",
            "sv2": "Vitesse située autour du second seuil.",
            "vma": "Vitesse comprise entre 95 et 105 % de la VMA.",
            "acceleration": "Hausse rapide de la vitesse détectée.",
            "sprint": "Vitesse supérieure à 105 % de la VMA.",
            "unknown": "Références individuelles insuffisantes.",
        }

        return labels.get(block_type, labels["unknown"])

    @staticmethod
    def _vma(
        profile: Optional[AthleteProfile],
    ) -> Optional[float]:
        if not profile:
            return None

        return profile.physiological.vma_kmh

    @staticmethod
    def _threshold_speed(
        profile: Optional[AthleteProfile],
    ) -> Optional[float]:
        if not profile:
            return None

        return profile.physiological.threshold_speed_kmh

    @staticmethod
    def _ordered_samples(
        samples: List[ActivitySample],
    ) -> List[ActivitySample]:
        return sorted(
            samples,
            key=lambda sample: DetailedSessionAnalyzer._date(
                sample.timestamp
            ),
        )

    @staticmethod
    def _date(value: str) -> datetime:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    @staticmethod
    def _average(
        values: List[float],
    ) -> Optional[float]:
        if not values:
            return None

        return mean(values)

    @classmethod
    def _sample_average(
        cls,
        samples: List[ActivitySample],
        field_name: str,
    ) -> Optional[float]:
        values = [
            value
            for sample in samples
            if (
                value := getattr(sample, field_name)
            ) is not None
        ]

        return cls._average(values)

    @staticmethod
    def _sample_maximum(
        samples: List[ActivitySample],
        field_name: str,
    ) -> Optional[float]:
        values = [
            value
            for sample in samples
            if (
                value := getattr(sample, field_name)
            ) is not None
        ]

        if not values:
            return None

        return max(values)
