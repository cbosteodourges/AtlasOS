"""
ATLAS OS
Analyse détaillée des points, tours et zones d'une séance FIT.
"""

from datetime import datetime
from statistics import mean, median
from typing import List, Optional, Tuple

from src.connectors import ActivitySample

from .athlete_profile import AthleteProfile
from .longitudinal_models import LongitudinalActivity
from .session_fingerprint import (
    DataIntegrityAssessment,
    DetailedSessionAnalysis,
    SessionBlock,
    ThresholdObservation,
    WorkoutExecutionSummary,
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
        data_integrity = self._data_integrity(
            activity,
            profile,
        )

        if len(samples) < 2:
            return DetailedSessionAnalysis(
                activity_id=activity.atlas_id,
                data_integrity=data_integrity,
                analysis_confidence_score=0,
                interpretation=[
                    "Points FIT insuffisants pour détecter "
                    "les blocs de la séance ; Atlas ne classe "
                    "pas cette activité."
                ],
            )

        vma_kmh = self._vma(profile)
        threshold_speed_kmh = self._threshold_speed(
            profile
        )
        is_cycling = self._is_cycling(activity)
        analysis_laps = self._analysis_laps(activity)
        if is_cycling:
            blocks = self._cycling_blocks(activity, profile)
        elif analysis_laps:
            blocks = self._blocks_from_laps(
                activity,
                vma_kmh,
                threshold_speed_kmh,
                laps=analysis_laps,
            )
        else:
            intervals = self._build_intervals(
                samples,
                vma_kmh,
                threshold_speed_kmh,
            )
            blocks = self._group_intervals(
                intervals
            )
        blocks = self._mark_session_boundaries(blocks)

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
        session_type = self._session_type(
            activity,
            work_blocks,
            dominant_work_type,
        )
        workout_execution = self._workout_execution(
            activity,
            blocks,
        )
        partial_work_duration = (
            self._structured_partial_work_duration(
                activity,
                samples,
                blocks,
                threshold_speed_kmh,
            )
        )
        threshold_observations = (
            [] if is_cycling
            else self._threshold_observations(blocks)
        )

        if not data_integrity.heart_rate_reliable:
            for observation in threshold_observations:
                observation.estimated_heart_rate_bpm = None
                observation.evidence.append(
                    "Fréquence cardiaque exclue par le "
                    "contrôle d'intégrité."
                )

        return DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            data_integrity=data_integrity,
            workout_execution=workout_execution,

            blocks=blocks,
            threshold_observations=threshold_observations,

            dominant_work_type=dominant_work_type,
            session_type=session_type,
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
            partial_work_duration_seconds=(
                partial_work_duration
            ),
            physiological_load_score=(
                physiological_load
            ),
            biomechanical_load_score=(
                biomechanical_load
            ),
            analysis_confidence_score=confidence,
            interpretation=self._interpretation(
                activity,
                blocks,
                dominant_work_type,
                session_type,
                workout_execution,
            ),
            planning_influences=(
                self._planning_influences(
                    blocks,
                    physiological_load,
                    biomechanical_load,
                    workout_execution,
                )
            ),
        )

    def _structured_partial_work_duration(
        self,
        activity: LongitudinalActivity,
        samples: List[ActivitySample],
        blocks: List[SessionBlock],
        threshold_speed_kmh: Optional[float],
    ) -> float:
        """Isole le travail d'un tour manuel mêlant effort et récupération.

        Sur une séance chronométrée, un Auto Lap suivi d'un appui manuel peut
        produire un bloc unique contenant la fin de l'effort puis le début de
        la récupération. La première chute de vitesse durable sous la cible
        marque alors la fin réelle du travail spécifique.
        """
        if not activity.workout_steps or len(samples) < 2:
            return 0.0

        active_steps = [
            step for step in activity.workout_steps
            if str(step.get("intensity", "")).lower()
            in {"active", "interval"}
            and self._number(step.get("duration_time"))
        ]
        if not active_steps:
            return 0.0

        target_duration = self._number(
            active_steps[0].get("duration_time")
        )
        if not target_duration:
            return 0.0

        target_speed_low = self._number(
            active_steps[0].get("custom_target_speed_low")
        )
        if target_speed_low is None and threshold_speed_kmh:
            target_speed_low = threshold_speed_kmh * 0.90 / 3.6
        if not target_speed_low:
            return 0.0

        candidates = [
            block for block in blocks
            if block.duration_seconds > target_duration + 5
            and any(
                "manuel" in reason.lower()
                for reason in block.detection_reasons
            )
        ]
        if not candidates:
            return 0.0

        session_start = self._date(samples[0].timestamp)
        cutoff_speed = target_speed_low * 0.90

        for block in candidates:
            block_samples = [
                sample for sample in samples
                if block.start_offset_seconds <= (
                    self._date(sample.timestamp) - session_start
                ).total_seconds() <= block.end_offset_seconds
            ]
            for index, sample in enumerate(block_samples):
                offset = (
                    self._date(sample.timestamp) - session_start
                ).total_seconds() - block.start_offset_seconds
                if offset < target_duration * 0.50:
                    continue
                if sample.speed_mps is None or sample.speed_mps >= cutoff_speed:
                    continue

                sustained = [
                    following for following in block_samples[index:]
                    if (
                        self._date(following.timestamp)
                        - self._date(sample.timestamp)
                    ).total_seconds() <= 10
                ]
                if len(sustained) < 5:
                    continue
                if all(
                    following.speed_mps is not None
                    and following.speed_mps < cutoff_speed
                    for following in sustained
                ):
                    return round(offset, 3)

        return 0.0

    @staticmethod
    def _is_cycling(activity: LongitudinalActivity) -> bool:
        activity_type = str(activity.activity_type or "").strip().lower()
        return (
            "cycling" in activity_type
            or "cyclisme" in activity_type
            or "biking" in activity_type
            or activity_type in {
                "road",
                "bike",
                "vtt",
                "mountain_biking",
                "gravel_cycling",
            }
        )

    @classmethod
    def _cycling_blocks(
        cls,
        activity: LongitudinalActivity,
        profile: Optional[AthleteProfile] = None,
    ) -> List[SessionBlock]:
        """Conserve une sortie vélo continue sans interpréter les Auto Lap.

        Les tours distance Garmin servent à l'affichage des kilomètres, pas
        à détecter des répétitions. Ils ne doivent donc jamais devenir des
        sprints ou des zones de course à pied.
        """
        duration_seconds = max(0.0, activity.duration_minutes * 60)
        if duration_seconds <= 0:
            return []
        physiological_load = min(100, round(activity.duration_minutes / 4))
        biomechanical_load = min(100, round(activity.duration_minutes / 10))
        corrected_maximum, spike_filtered = cls._sustained_heart_rate_maximum(
            activity,
            profile,
        )
        reasons = [
            "Sortie vélo analysée comme un effort continu ; tours distance Garmin neutralisés."
        ]
        if spike_filtered:
            reasons.append(
                "Pic cardiaque isolé neutralisé ; la FC maximale affichée correspond à un effort soutenu."
            )
        return [SessionBlock(
            block_index=1,
            block_type="cycling",
            start_offset_seconds=0.0,
            end_offset_seconds=duration_seconds,
            duration_seconds=duration_seconds,
            distance_meters=max(0.0, activity.distance_km * 1000),
            average_speed_kmh=activity.average_speed_kmh,
            maximum_speed_kmh=max(
                (
                    cls._number(lap.get("enhanced_max_speed", lap.get("max_speed")))
                    or 0.0
                ) * 3.6
                for lap in (activity.laps or [{}])
            ) or activity.average_speed_kmh,
            average_heart_rate_bpm=activity.average_heart_rate_bpm,
            maximum_heart_rate_bpm=corrected_maximum,
            average_power_watts=activity.dynamics.average_power_watts,
            average_cadence_spm=activity.dynamics.average_cadence_spm,
            physiological_load_score=physiological_load,
            biomechanical_load_score=biomechanical_load,
            confidence_score=max(70, min(95, activity.data_quality_score or 85)),
            detection_reasons=reasons,
        )]

    @classmethod
    def _sustained_heart_rate_maximum(
        cls,
        activity: LongitudinalActivity,
        profile: Optional[AthleteProfile] = None,
    ) -> tuple[Optional[float], bool]:
        """Écarte les pics cardio optiques sans effacer la mesure Garmin."""
        raw_maximum = activity.maximum_heart_rate_bpm
        ordered = [
            sample
            for sample in cls._ordered_samples(activity.samples)
            if sample.heart_rate_bpm is not None
            and 30 <= float(sample.heart_rate_bpm) <= 240
        ]
        values = [float(sample.heart_rate_bpm) for sample in ordered]
        if not values:
            return raw_maximum, False

        def sustained_maximum(series: List[float]) -> float:
            if len(series) < 15:
                return max(series)
            return max(
                median(series[index:index + 15])
                for index in range(len(series) - 14)
            )

        # Le filtre médian neutralise les décrochages très courts.
        sustained = sustained_maximum(values)
        observed_raw = max(
            [float(raw_maximum)] if raw_maximum is not None else []
            + values
        )
        spike_filtered = len(values) >= 15 and observed_raw - sustained >= 10

        # Une mauvaise acquisition optique peut toutefois durer plusieurs
        # minutes au démarrage (montre froide, peau sèche, cadence verrouillée).
        # Sur une sortie facile, un plateau initial proche de la FC maximale
        # connue, suivi d'une courbe durablement bien plus basse, n'est pas un
        # véritable effort maximal. On conserve le brut mais on retient le
        # maximum soutenu observé après la phase d'acquisition.
        declared_maximum = (
            profile.physiological.maximum_heart_rate_bpm
            if profile
            else None
        )
        if (
            declared_maximum is not None
            and len(ordered) >= 30
            and activity.average_heart_rate_bpm is not None
            and activity.average_heart_rate_bpm <= declared_maximum * 0.82
        ):
            start = cls._date(ordered[0].timestamp)
            acquisition_seconds = min(
                600.0,
                max(120.0, activity.duration_minutes * 60 * 0.20),
            )
            early_values = [
                float(sample.heart_rate_bpm)
                for sample in ordered
                if (cls._date(sample.timestamp) - start).total_seconds()
                <= acquisition_seconds
            ]
            later_values = [
                float(sample.heart_rate_bpm)
                for sample in ordered
                if (cls._date(sample.timestamp) - start).total_seconds()
                > acquisition_seconds
            ]
            if len(early_values) >= 15 and len(later_values) >= 15:
                early_sustained = sustained_maximum(early_values)
                later_sustained = sustained_maximum(later_values)
                acquisition_artifact = (
                    early_sustained >= declared_maximum - 3
                    and early_sustained - later_sustained >= 10
                )
                if acquisition_artifact:
                    sustained = later_sustained
                    spike_filtered = True

        return (
            round(sustained, 1) if spike_filtered else observed_raw,
            spike_filtered,
        )

    @staticmethod
    def _data_integrity(
        activity: LongitudinalActivity,
        profile: Optional[AthleteProfile],
    ) -> DataIntegrityAssessment:
        """Signale les données douteuses sans supprimer l'activité."""
        anomalies = []
        warnings = []
        heart_rate_reliable = True
        sensor_quality = 100
        identity_confidence = 100

        declared_maximum = (
            profile.physiological.maximum_heart_rate_bpm
            if profile
            else None
        )
        corrected_maximum, spike_filtered = (
            DetailedSessionAnalyzer._sustained_heart_rate_maximum(
                activity,
                profile,
            )
            if DetailedSessionAnalyzer._is_cycling(activity)
            else (activity.maximum_heart_rate_bpm, False)
        )
        observed_values = (
            [corrected_maximum]
            if spike_filtered and corrected_maximum is not None
            else [
                value
                for value in (
                    corrected_maximum,
                    *[
                        sample.heart_rate_bpm
                        for sample in activity.samples
                    ],
                )
                if value is not None
            ]
        )
        observed_maximum = (
            max(observed_values)
            if observed_values
            else None
        )
        if spike_filtered:
            warnings.append(
                "Pic cardiaque isolé probablement lié au capteur ; valeur brute conservée et maximum soutenu utilisé."
            )
            sensor_quality -= 5

        if (
            declared_maximum is not None
            and observed_maximum is not None
        ):
            excess = observed_maximum - declared_maximum

            if excess > 3:
                heart_rate_reliable = False
                sensor_quality -= 45
                identity_confidence -= 20
                anomalies.append(
                    (
                        "FC observée "
                        f"{observed_maximum:.0f} bpm supérieure "
                        "à la limite déclarée de "
                        f"{declared_maximum:.0f} bpm."
                    )
                )
            elif excess > 0:
                sensor_quality -= 10
                warnings.append(
                    (
                        "FC légèrement supérieure à la "
                        f"référence de {declared_maximum:.0f} bpm."
                    )
                )

        physiological_usable = heart_rate_reliable
        action = (
            "use_all_data"
            if heart_rate_reliable
            else "exclude_heart_rate"
        )

        return DataIntegrityAssessment(
            heart_rate_reliable=heart_rate_reliable,
            physiological_data_usable=(
                physiological_usable
            ),
            identity_confidence_score=max(
                0,
                identity_confidence,
            ),
            sensor_quality_score=max(
                0,
                sensor_quality,
            ),
            recommended_action=action,
            raw_maximum_heart_rate_bpm=activity.maximum_heart_rate_bpm,
            corrected_maximum_heart_rate_bpm=corrected_maximum,
            heart_rate_spike_filtered=spike_filtered,
            anomalies=anomalies,
            warnings=warnings,
        )
    @classmethod
    def _workout_execution(
        cls,
        activity: LongitudinalActivity,
        blocks: List[SessionBlock],
    ) -> WorkoutExecutionSummary:
        """Compare les étapes Garmin prévues aux tours exécutés."""
        if not activity.workout or not activity.workout_steps:
            return WorkoutExecutionSummary()

        raw_name = activity.workout[0].get("wkt_name", "")
        if isinstance(raw_name, list):
            workout_name = next(
                (
                    str(value)
                    for value in raw_name
                    if str(value).strip()
                ),
                "",
            )
        else:
            workout_name = str(raw_name or "")

        workout_payload = activity.workout[0]
        capabilities = str(
            workout_payload.get("capabilities", "")
        ).strip().lower()
        origin_marker = workout_payload.get(
            "9",
            workout_payload.get(9),
        )

        if (
            "tcx" in capabilities
            or origin_marker == 1
            or str(origin_marker) == "1"
        ):
            workout_origin = "user_created"
            origin_confidence = 95
            origin_reasons = [
                "Capacité TCX ou marqueur FIT utilisateur."
            ]
        elif (
            not capabilities
            and (
                origin_marker == 0
                or str(origin_marker) == "0"
            )
        ):
            workout_origin = "garmin_suggested"
            origin_confidence = 85
            origin_reasons = [
                "Programme Garmin sans capacité TCX.",
                "Marqueur FIT compatible avec une suggestion.",
            ]
        else:
            workout_origin = "unknown"
            origin_confidence = 40
            origin_reasons = [
                "Origine non explicitement fournie par Garmin."
            ]

        ordered_steps = sorted(
            activity.workout_steps,
            key=lambda step: int(
                step.get("message_index", 0)
            ),
        )

        def expand_steps(
            start: int,
            end: int,
        ) -> List[dict]:
            expanded = []

            for position in range(start, end):
                step = ordered_steps[position]
                duration_type = str(
                    step.get("duration_type", "")
                )

                if duration_type.startswith(
                    "repeat_until"
                ):
                    repeat_count = max(
                        1,
                        int(step.get("repeat_steps", 1)),
                    )
                    repeat_start = max(
                        start,
                        int(step.get("duration_step", 0)),
                    )
                    segment = expand_steps(
                        repeat_start,
                        position,
                    )

                    for _ in range(repeat_count - 1):
                        expanded.extend(segment)
                    continue

                expanded.append(step)

            return expanded

        expanded_steps = expand_steps(
            0,
            len(ordered_steps),
        )
        tolerance = 5
        block_cursor = 0
        matched_blocks = []

        for step_index, step in enumerate(expanded_steps):
            selected = []
            duration_target = step.get("duration_time")
            distance_target = step.get(
                "duration_distance"
            )
            duration_total = 0.0
            distance_total = 0.0

            while block_cursor < len(blocks):
                block = blocks[block_cursor]
                selected.append(block)
                block_cursor += 1
                duration_total += block.duration_seconds
                distance_total += block.distance_meters

                if duration_target is not None:
                    if (
                        duration_total
                        >= float(duration_target) - tolerance
                    ):
                        break
                elif distance_target is not None:
                    if (
                        distance_total
                        >= float(distance_target) * 0.90
                    ):
                        break
                elif (
                    step_index
                    == len(expanded_steps) - 1
                ):
                    selected.extend(
                        blocks[block_cursor:]
                    )
                    block_cursor = len(blocks)
                    break
                else:
                    break

            matched_blocks.append(selected)

        planned_active_positions = [
            index
            for index, step in enumerate(expanded_steps)
            if str(step.get("intensity", "")).lower()
            in {"active", "interval"}
        ]
        completed_active_count = 0
        target_scores = []
        recovery_scores = []

        for index in planned_active_positions:
            if index >= len(matched_blocks):
                continue

            selected = matched_blocks[index]
            if not selected:
                continue

            step = expanded_steps[index]
            duration_total = sum(
                block.duration_seconds
                for block in selected
            )
            distance_total = sum(
                block.distance_meters
                for block in selected
            )
            duration_target = step.get("duration_time")
            distance_target = step.get(
                "duration_distance"
            )
            completed = True

            if duration_target is not None:
                completed = (
                    abs(
                        duration_total
                        - float(duration_target)
                    )
                    <= tolerance
                )
            elif distance_target is not None:
                target_distance = float(distance_target)
                completed = (
                    target_distance > 0
                    and abs(
                        distance_total - target_distance
                    )
                    / target_distance
                    <= 0.10
                )

            if completed:
                completed_active_count += 1

            minimum_speed = step.get(
                "custom_target_speed_low"
            )
            maximum_speed = step.get(
                "custom_target_speed_high"
            )
            speed_blocks = [
                block
                for block in selected
                if block.average_speed_kmh is not None
            ]

            if (
                minimum_speed is None
                or maximum_speed is None
                or not speed_blocks
            ):
                continue

            total_weight = sum(
                max(block.duration_seconds, 1)
                for block in speed_blocks
            )
            actual_speed_mps = (
                sum(
                    block.average_speed_kmh
                    * max(block.duration_seconds, 1)
                    for block in speed_blocks
                )
                / total_weight
                / 3.6
            )
            low = float(minimum_speed)
            high = float(maximum_speed)

            if low <= actual_speed_mps <= high:
                target_scores.append(100)
            else:
                difference = min(
                    abs(actual_speed_mps - low),
                    abs(actual_speed_mps - high),
                )
                target_scores.append(
                    max(0, round(100 - difference * 50))
                )

        for index, step in enumerate(expanded_steps):
            if str(step.get("intensity", "")).lower() != "recovery":
                continue
            target = cls._number(step.get("duration_time"))
            if not target or index >= len(matched_blocks):
                continue
            actual = sum(
                block.duration_seconds for block in matched_blocks[index]
            )
            ratio = actual / target
            recovery_scores.append(
                100 if 0.9 <= ratio <= 1.15
                else max(0, round(100 - abs(1 - ratio) * 100))
            )

        planned_active_count = len(
            planned_active_positions
        )
        completion_score = (
            round(
                completed_active_count
                / planned_active_count
                * 100
            )
            if planned_active_count
            else 100
        )
        matched_step_count = sum(
            bool(selected)
            for selected in matched_blocks
        )
        step_score = (
            round(
                matched_step_count
                / len(expanded_steps)
                * 100
            )
            if expanded_steps
            else 100
        )
        target_score = (
            round(mean(target_scores))
            if target_scores
            else completion_score
        )
        execution_score = round(
            completion_score * (0.4 if recovery_scores else 0.5)
            + target_score * 0.3
            + step_score * (0.15 if recovery_scores else 0.2)
            + ((round(mean(recovery_scores)) * 0.15) if recovery_scores else 0)
        )
        recovery_score = round(mean(recovery_scores)) if recovery_scores else None

        observations = [
            (
                f"{completed_active_count}/"
                f"{planned_active_count} blocs actifs "
                "réalisés."
            ),
            (
                f"Respect des cibles : "
                f"{target_score}/100."
            ),
            (
                "Transitions de 5 secondes ou moins "
                "neutralisées."
            ),
        ]
        if recovery_score is not None:
            observations.append(
                f"Respect des récupérations : {recovery_score}/100."
            )
            if recovery_score < 70:
                observations.append(
                    "Récupération écourtée détectée ; le score d'exécution est réduit."
                )

        return WorkoutExecutionSummary(
            workout_name=workout_name,
            workout_origin=workout_origin,
            origin_confidence_score=origin_confidence,
            origin_reasons=origin_reasons,
            planned_step_count=len(expanded_steps),
            executed_block_count=len(blocks),
            planned_repetition_count=(
                planned_active_count
            ),
            completed_repetition_count=(
                completed_active_count
            ),
            target_compliance_score=target_score,
            recovery_compliance_score=recovery_score,
            execution_score=min(100, execution_score),
            countdown_tolerance_seconds=tolerance,
            observations=observations,
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

    @staticmethod
    def _has_manual_laps(
        laps: List[dict],
    ) -> bool:
        return any(
            str(lap.get("lap_trigger", "")).lower()
            == "manual"
            for lap in laps
        )

    @classmethod
    def _analysis_laps(
        cls,
        activity: LongitudinalActivity,
    ) -> List[dict]:
        """Neutralise les tours distance dans une séance structurée.

        Garmin peut fermer un tour kilométrique au milieu d'une étape
        chronométrée. Ce tour et la fin de l'étape sont alors séquentiels :
        Atlas les fusionne jusqu'au prochain marqueur workout_step, manuel
        ou de fin de séance. Sur une sortie libre, les tours restent intacts.
        """
        laps = list(activity.laps or [])
        if not laps or not activity.workout_steps:
            return laps

        boundaries = {
            "manual",
            "time",
            "workout_step",
            "session_end",
        }
        groups: List[List[dict]] = []
        pending: List[dict] = []

        for lap in laps:
            pending.append(lap)
            trigger = str(
                lap.get("lap_trigger", "")
            ).strip().lower()
            if trigger in boundaries:
                groups.append(pending)
                pending = []

        if pending:
            groups.append(pending)

        return [
            cls._merge_structured_laps(group)
            for group in groups
            if group
        ]

    @classmethod
    def _merge_structured_laps(
        cls,
        laps: List[dict],
    ) -> dict:
        """Réunit les fragments Auto Lap appartenant à la même étape."""
        if len(laps) == 1:
            return dict(laps[0])

        merged = dict(laps[-1])
        duration_fields = (
            "total_timer_time",
            "total_elapsed_time",
        )
        for field in duration_fields:
            values = [cls._number(lap.get(field)) for lap in laps]
            available = [value for value in values if value is not None]
            if available:
                merged[field] = sum(available)

        distances = [
            cls._number(lap.get("total_distance"))
            for lap in laps
        ]
        available_distances = [
            value for value in distances if value is not None
        ]
        if available_distances:
            merged["total_distance"] = sum(available_distances)

        durations = [
            cls._number(
                lap.get(
                    "total_timer_time",
                    lap.get("total_elapsed_time"),
                )
            ) or 0.0
            for lap in laps
        ]
        weighted_fields = (
            "avg_heart_rate",
            "avg_power",
            "avg_running_cadence",
            "avg_cadence",
            "avg_stance_time",
            "avg_vertical_ratio",
            "avg_step_length",
            "avg_vertical_oscillation",
        )
        for field in weighted_fields:
            weighted = [
                (cls._number(lap.get(field)), duration)
                for lap, duration in zip(laps, durations)
                if cls._number(lap.get(field)) is not None
                and duration > 0
            ]
            if weighted:
                merged[field] = sum(
                    value * duration for value, duration in weighted
                ) / sum(duration for _value, duration in weighted)

        for field in ("max_heart_rate", "enhanced_max_speed", "max_speed"):
            values = [cls._number(lap.get(field)) for lap in laps]
            available = [value for value in values if value is not None]
            if available:
                merged[field] = max(available)

        total_duration = cls._number(
            merged.get("total_timer_time")
        )
        total_distance = cls._number(
            merged.get("total_distance")
        )
        if total_duration and total_distance is not None:
            merged["enhanced_avg_speed"] = (
                total_distance / total_duration
            )

        merged["start_time"] = laps[0].get(
            "start_time",
            merged.get("start_time"),
        )
        merged["atlas_merged_auto_laps"] = len(laps) - 1
        return merged

    def _blocks_from_laps(
        self,
        activity: LongitudinalActivity,
        vma_kmh: Optional[float],
        threshold_speed_kmh: Optional[float],
        laps: Optional[List[dict]] = None,
    ) -> List[SessionBlock]:
        """Utilise les limites d'étapes Garmin comme structure prioritaire."""
        blocks = []
        elapsed = 0.0
        previous_type = None
        laps = laps if laps is not None else activity.laps

        for index, lap in enumerate(laps, start=1):
            duration = self._number(
                lap.get(
                    "total_timer_time",
                    lap.get("total_elapsed_time"),
                )
            ) or 0.0
            distance = self._number(
                lap.get("total_distance")
            ) or 0.0
            average_speed_mps = self._number(
                lap.get(
                    "enhanced_avg_speed",
                    lap.get("avg_speed"),
                )
            )
            maximum_speed_mps = self._number(
                lap.get(
                    "enhanced_max_speed",
                    lap.get("max_speed"),
                )
            )
            average_speed_kmh = (
                average_speed_mps * 3.6
                if average_speed_mps is not None
                else (
                    distance / duration * 3.6
                    if duration > 0
                    else None
                )
            )
            maximum_speed_kmh = (
                maximum_speed_mps * 3.6
                if maximum_speed_mps is not None
                else average_speed_kmh
            )
            trigger = str(
                lap.get("lap_trigger", "")
            ).lower()

            block_type = self._lap_block_type(
                index=index,
                lap_count=len(laps),
                trigger=trigger,
                duration_seconds=duration,
                average_speed_kmh=average_speed_kmh,
                maximum_speed_kmh=maximum_speed_kmh,
                previous_type=previous_type,
                vma_kmh=vma_kmh,
                threshold_speed_kmh=(
                    threshold_speed_kmh
                ),
            )

            cadence = self._number(
                lap.get(
                    "avg_running_cadence",
                    lap.get("avg_cadence"),
                )
            )
            if cadence is not None:
                cadence *= 2

            block = SessionBlock(
                block_index=index,
                block_type=block_type,
                start_offset_seconds=elapsed,
                end_offset_seconds=(
                    elapsed + duration
                ),
                duration_seconds=duration,
                distance_meters=distance,
                average_speed_kmh=average_speed_kmh,
                maximum_speed_kmh=maximum_speed_kmh,
                average_heart_rate_bpm=self._number(
                    lap.get("avg_heart_rate")
                ),
                maximum_heart_rate_bpm=self._number(
                    lap.get("max_heart_rate")
                ),
                average_power_watts=self._number(
                    lap.get("avg_power")
                ),
                average_cadence_spm=cadence,
                average_stride_length_m=(
                    self._scaled_number(
                        lap.get("avg_step_length"),
                        1000,
                    )
                ),
                average_vertical_ratio_percent=(
                    self._number(
                        lap.get("avg_vertical_ratio")
                    )
                ),
                average_vertical_oscillation_cm=(
                    self._scaled_number(
                        lap.get(
                            "avg_vertical_oscillation"
                        ),
                        10,
                    )
                ),
                average_ground_contact_time_ms=(
                    self._number(
                        lap.get("avg_stance_time")
                    )
                ),
                physiological_load_score=(
                    self._physiological_load(
                        block_type,
                        duration,
                    )
                ),
                biomechanical_load_score=(
                    self._lap_biomechanical_load(
                        block_type,
                        duration,
                        lap,
                    )
                ),
                confidence_score=(
                    95 if trigger == "manual" else 85
                ),
                detection_reasons=[
                    (
                        "Tour manuel marqué par "
                        "l'athlète."
                        if trigger == "manual"
                        else
                        "Tour automatique Garmin."
                    )
                ],
            )
            blocks.append(block)
            previous_type = block_type
            elapsed += duration

        return blocks

    def _lap_block_type(
        self,
        index: int,
        lap_count: int,
        trigger: str,
        duration_seconds: float,
        average_speed_kmh: Optional[float],
        maximum_speed_kmh: Optional[float],
        previous_type: Optional[str],
        vma_kmh: Optional[float],
        threshold_speed_kmh: Optional[float],
    ) -> str:
        if index == 1 and trigger != "manual":
            return "warm_up"

        if (
            index == lap_count
            and trigger == "session_end"
        ):
            return "cool_down"

        average_speed = average_speed_kmh or 0.0
        maximum_speed = (
            maximum_speed_kmh
            if maximum_speed_kmh is not None
            else average_speed
        )

        if (
            trigger == "manual"
            and duration_seconds <= 30
            and vma_kmh
            and maximum_speed >= vma_kmh * 1.05
        ):
            return "sprint"

        if (
            trigger == "manual"
            and duration_seconds <= 30
            and vma_kmh
            and average_speed >= vma_kmh * 0.75
        ):
            return "acceleration"

        base_type = self._block_type(
            average_speed,
            0.0,
            vma_kmh,
            threshold_speed_kmh,
        )

        if (
            trigger in {"manual", "time"}
            and previous_type
            in {
                "acceleration",
                "sprint",
                "vma",
                "sv2",
            }
            and base_type in {"z1", "z2"}
        ):
            return "recovery"

        return base_type

    @staticmethod
    def _lap_biomechanical_load(
        block_type: str,
        duration_seconds: float,
        lap: dict,
    ) -> int:
        intensity = {
            "warm_up": 0.5,
            "cool_down": 0.5,
            "recovery": 0.4,
            "z1": 0.6,
            "z2": 0.8,
            "z3": 1.2,
            "sv2": 1.7,
            "vma": 2.4,
            "acceleration": 2.8,
            "sprint": 3.5,
        }.get(block_type, 0.6)

        dynamics_count = sum(
            1
            for field_name in (
                "avg_running_cadence",
                "avg_stance_time",
                "avg_vertical_ratio",
                "avg_step_length",
            )
            if lap.get(field_name) is not None
        )

        return max(
            0,
            round(
                duration_seconds
                / 60
                * intensity
                * (1 + dynamics_count * 0.05)
            ),
        )

    @staticmethod
    def _number(
        value,
    ) -> Optional[float]:
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _scaled_number(
        cls,
        value,
        divisor: float,
    ) -> Optional[float]:
        number = cls._number(value)

        if number is None:
            return None

        return number / divisor

    def _build_intervals(
        self,
        samples: List[ActivitySample],
        vma_kmh: Optional[float],
        threshold_speed_kmh: Optional[float],
    ) -> List[Tuple[str, ActivitySample, float, float, float]]:
        intervals = []
        smoothed_speeds = self._smoothed_speeds(
            samples
        )
        previous_type = None

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

            speed = smoothed_speeds[index]
            previous_speed = (
                smoothed_speeds[index - 1]
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
            block_type = self._stabilize_zone_boundary(
                block_type,
                previous_type,
                speed * 3.6,
                vma_kmh,
            )
            previous_type = block_type
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

        return self._mark_recoveries(intervals)

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
        groups = self._merge_short_groups(groups)

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

    @staticmethod
    def _mark_session_boundaries(
        blocks: List[SessionBlock],
    ) -> List[SessionBlock]:
        """Identifie échauffement et retour au calme autour d'un travail réel."""
        if len(blocks) < 3:
            return blocks

        total_duration = sum(block.duration_seconds for block in blocks)
        if total_duration < 15 * 60:
            return blocks

        intense_types = {"z3", "sv2", "vma", "acceleration", "sprint"}
        easy_types = {"z1", "z2", "recovery"}
        if not any(block.block_type in intense_types for block in blocks[1:-1]):
            return blocks

        first = blocks[0]
        if first.block_type in easy_types and first.duration_seconds <= 25 * 60:
            first.block_type = "warm_up"
            first.detection_reasons.append(
                "Bloc facile initial précédant un travail d'intensité."
            )

        last = blocks[-1]
        if last.block_type in easy_types and last.duration_seconds <= 25 * 60:
            last.block_type = "cool_down"
            last.detection_reasons.append(
                "Bloc facile terminal suivant un travail d'intensité."
            )
        return blocks

    @classmethod
    def _merge_short_groups(
        cls,
        groups: List[
            List[
                Tuple[
                    str,
                    ActivitySample,
                    float,
                    float,
                    float,
                ]
            ]
        ],
    ) -> List[
        List[
            Tuple[
                str,
                ActivitySample,
                float,
                float,
                float,
            ]
        ]
    ]:
        """Fusionne les variations trop courtes pour être fiables."""
        minimum_durations = {
            "acceleration": 3.0,
            "sprint": 3.0,
            "recovery": 5.0,
            "vma": 8.0,
            "sv2": 10.0,
            "z3": 10.0,
            "z2": 10.0,
            "z1": 10.0,
            "unknown": 10.0,
        }
        merged = [list(group) for group in groups]
        changed = True

        while changed and len(merged) > 1:
            changed = False

            for index, group in enumerate(merged):
                block_type = group[0][0]
                duration = sum(
                    interval[2]
                    for interval in group
                )
                minimum = minimum_durations.get(
                    block_type,
                    10.0,
                )

                if duration >= minimum:
                    continue

                left = (
                    merged[index - 1]
                    if index > 0
                    else None
                )
                right = (
                    merged[index + 1]
                    if index + 1 < len(merged)
                    else None
                )

                if left is None and right is None:
                    continue

                if (
                    left is not None
                    and right is not None
                    and left[0][0] == right[0][0]
                ):
                    target_type = left[0][0]
                    combined = (
                        left
                        + cls._relabel_group(
                            group,
                            target_type,
                        )
                        + right
                    )
                    merged[index - 1:index + 2] = [
                        combined
                    ]

                elif right is None:
                    target_type = left[0][0]
                    left.extend(
                        cls._relabel_group(
                            group,
                            target_type,
                        )
                    )
                    del merged[index]

                elif left is None:
                    target_type = right[0][0]
                    merged[index + 1] = (
                        cls._relabel_group(
                            group,
                            target_type,
                        )
                        + right
                    )
                    del merged[index]

                else:
                    left_duration = sum(
                        interval[2]
                        for interval in left
                    )
                    right_duration = sum(
                        interval[2]
                        for interval in right
                    )

                    if left_duration >= right_duration:
                        target_type = left[0][0]
                        left.extend(
                            cls._relabel_group(
                                group,
                                target_type,
                            )
                        )
                        del merged[index]
                    else:
                        target_type = right[0][0]
                        merged[index + 1] = (
                            cls._relabel_group(
                                group,
                                target_type,
                            )
                            + right
                        )
                        del merged[index]

                changed = True
                break

        return merged

    @staticmethod
    def _relabel_group(
        group: List[
            Tuple[str, ActivitySample, float, float, float]
        ],
        block_type: str,
    ) -> List[
        Tuple[str, ActivitySample, float, float, float]
    ]:
        return [
            (
                block_type,
                interval[1],
                interval[2],
                interval[3],
                interval[4],
            )
            for interval in group
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

    @staticmethod
    def _smoothed_speeds(
        samples: List[ActivitySample],
        radius: int = 2,
    ) -> List[float]:
        """Lisse la vitesse avec une médiane glissante."""
        speeds = [
            sample.speed_mps or 0.0
            for sample in samples
        ]
        smoothed = []

        for index in range(len(speeds)):
            start = max(0, index - radius)
            end = min(
                len(speeds),
                index + radius + 1,
            )
            smoothed.append(
                float(median(speeds[start:end]))
            )

        return smoothed

    @staticmethod
    def _stabilize_zone_boundary(
        block_type: str,
        previous_type: Optional[str],
        speed_kmh: float,
        vma_kmh: Optional[float],
    ) -> str:
        """Évite les bascules répétées autour de Z1–Z2."""
        if (
            previous_type not in {"z1", "z2"}
            or not vma_kmh
            or vma_kmh <= 0
        ):
            return block_type

        vma_percent = speed_kmh / vma_kmh * 100

        if 63 <= vma_percent <= 67:
            return previous_type

        return block_type

    @staticmethod
    def _mark_recoveries(
        intervals: List[
            Tuple[str, ActivitySample, float, float, float]
        ],
    ) -> List[
        Tuple[str, ActivitySample, float, float, float]
    ]:
        """Identifie une récupération après haute intensité."""
        result = []
        recovery_context = False

        for interval in intervals:
            block_type = interval[0]

            if block_type in {
                "acceleration",
                "sv2",
                "vma",
                "sprint",
            }:
                recovery_context = True

            elif (
                block_type == "z1"
                and recovery_context
            ):
                interval = (
                    "recovery",
                    interval[1],
                    interval[2],
                    interval[3],
                    interval[4],
                )

            elif block_type == "z2":
                recovery_context = False

            result.append(interval)

        return result

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
            return "z1"
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
            "z1": 0.7,
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
            "z1": 0.6,
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
        if any(
            str(lap.get("lap_trigger", "")).lower()
            == "manual"
            for lap in activity.laps
        ):
            score += 30
        elif activity.laps:
            score += 10
        score += 10 if activity.time_in_zones else 0

        has_manual_laps = any(
            str(lap.get("lap_trigger", "")).lower()
            == "manual"
            for lap in activity.laps
        )

        if has_manual_laps:
            maximum_confidence = 95
        elif activity.laps:
            maximum_confidence = 85
        else:
            maximum_confidence = 75

        return min(maximum_confidence, score)

    @staticmethod
    def _dominant_type(
        blocks: List[SessionBlock],
    ) -> str:
        if not blocks:
            return "unknown"

        rapid_blocks = [
            block
            for block in blocks
            if block.block_type
            in {"sprint", "acceleration"}
        ]

        if len(rapid_blocks) >= 3:
            return "sprint_acceleration"

        durations = {}

        for block in blocks:
            durations[block.block_type] = (
                durations.get(block.block_type, 0.0)
                + block.duration_seconds
            )

        return max(durations, key=durations.get)

    @staticmethod
    def _session_type(
        activity: LongitudinalActivity,
        work_blocks: List[SessionBlock],
        dominant_work_type: str,
    ) -> str:
        """Classe la nature globale sans déduire une intensité absente."""
        if DetailedSessionAnalyzer._is_cycling(activity):
            return "cycling"
        types = {block.block_type for block in work_blocks}
        if not work_blocks or dominant_work_type == "unknown":
            return "unknown"
        if types & {"sprint", "acceleration", "vma"}:
            return "vma"
        if "sv2" in types:
            return "threshold"
        if dominant_work_type == "z3":
            return "tempo"
        if dominant_work_type == "z1":
            return "recovery"
        if dominant_work_type == "z2":
            if activity.duration_minutes >= 75 or activity.distance_km >= 12:
                return "long_run"
            return "endurance"
        return "unknown"

    @staticmethod
    def _interpretation(
        activity: LongitudinalActivity,
        blocks: List[SessionBlock],
        dominant_work_type: str,
        session_type: str,
        workout_execution: WorkoutExecutionSummary,
    ) -> List[str]:
        if not blocks:
            return [
                "Aucun bloc exploitable n'a été détecté."
            ]

        labels = {
            "recovery": "footing de récupération",
            "endurance": "endurance fondamentale",
            "long_run": "sortie longue à dominante endurance",
            "tempo": "travail tempo",
            "threshold": "travail au seuil",
            "vma": "travail VMA ou vitesse",
            "cycling": "sortie vélo",
            "unknown": "nature non déterminée",
        }
        interpretation = [
            f"{len(blocks)} blocs homogènes détectés.",
            (
                "Nature de séance : "
                f"{labels.get(session_type, session_type)}."
            ),
        ]
        if session_type == "unknown":
            interpretation.append(
                "Les données disponibles ne permettent pas une classification fiable."
            )

        work_blocks = [
            block for block in blocks
            if block.block_type not in {"warm_up", "recovery", "cool_down"}
        ]

        def weighted(field: str) -> Optional[float]:
            available = [
                block for block in work_blocks
                if getattr(block, field, None) is not None
            ]
            duration = sum(max(1.0, block.duration_seconds) for block in available)
            if not available or duration <= 0:
                return None
            return sum(
                float(getattr(block, field)) * max(1.0, block.duration_seconds)
                for block in available
            ) / duration

        metrics = []
        for label, field, unit, digits in (
            ("vitesse", "average_speed_kmh", " km/h", 2),
            ("FC", "average_heart_rate_bpm", " bpm", 0),
            ("puissance", "average_power_watts", " W", 0),
            ("cadence", "average_cadence_spm", " pas/min", 0),
        ):
            value = weighted(field)
            if value is not None:
                metrics.append(f"{label} {value:.{digits}f}{unit}")
        if metrics:
            interpretation.append(
                "Bloc(s) de travail — " + " · ".join(metrics) + "."
            )
        if activity.elevation_gain_m is not None:
            interpretation.append(
                f"Dénivelé positif enregistré : {activity.elevation_gain_m:.0f} m."
            )
        if not metrics:
            interpretation.append(
                "Aucune moyenne fiable de vitesse, FC, puissance ou cadence pour les blocs de travail."
            )

        if workout_execution.workout_name:
            interpretation.append(
                (
                    "Programme Garmin "
                    f"« {workout_execution.workout_name} » : "
                    f"{workout_execution.completed_repetition_count}/"
                    f"{workout_execution.planned_repetition_count} "
                    "blocs actifs réalisés, score d'exécution "
                    f"{workout_execution.execution_score}/100."
                )
            )

        return interpretation
    @staticmethod
    def _planning_influences(
        blocks: List[SessionBlock],
        physiological_load: int,
        biomechanical_load: int,
        workout_execution: WorkoutExecutionSummary,
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

        if workout_execution.workout_name:
            completed = (
                workout_execution
                .completed_repetition_count
            )
            planned = (
                workout_execution
                .planned_repetition_count
            )

            if (
                planned > 0
                and completed >= planned
                and workout_execution.execution_score >= 90
                and workout_execution.target_compliance_score
                >= 85
            ):
                influences.append(
                    "Séance programmée maîtrisée : autoriser "
                    "une progression prudente du volume ou de "
                    "l'allure lors d'une prochaine séance "
                    "comparable, si la récupération est bonne."
                )
            elif workout_execution.execution_score >= 70:
                influences.append(
                    "Conserver les mêmes paramètres sur une "
                    "prochaine séance comparable avant toute "
                    "progression."
                )
            else:
                influences.append(
                    "Ne pas augmenter cette séance : la "
                    "répéter ou alléger son volume jusqu'à "
                    "une exécution plus stable."
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
            "recovery": "Allure basse après un bloc intense.",
            "z1": "Vitesse inférieure à 65 % de la VMA.",
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
