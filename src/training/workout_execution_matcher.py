"""
ATLAS OS
Rapproche une séance planifiée Atlas et une activité réellement exécutée.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from types import SimpleNamespace
from typing import Optional

from src.performance import (
    DetailedSessionAnalysis,
    LongitudinalActivity,
    WorkoutExecutionSummary,
)

from .session_models import (
    AdaptiveWorkout,
    BlockType,
    TrainingBlock,
    WorkoutType,
)


@dataclass(slots=True)
class AtlasWorkoutExecutionMatch:
    """Résultat du rapprochement entre le calendrier et le FIT."""

    workout_id: str
    activity_id: str
    matched: bool
    match_confidence_score: int
    execution: WorkoutExecutionSummary
    date_difference_days: int = 0
    duration_compliance_score: Optional[int] = None
    distance_compliance_score: Optional[int] = None
    target_compliance_score: Optional[int] = None
    physiological_load_score: int = 0
    biomechanical_load_score: int = 0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Convertit le résultat en dictionnaire sérialisable."""
        result = asdict(self)
        return result


class AtlasWorkoutExecutionMatcher:
    """Compare une activité réelle à une séance Atlas planifiée."""

    MATCH_THRESHOLD = 70

    def match(
        self,
        planned_workout: AdaptiveWorkout,
        activity: LongitudinalActivity,
        analysis: DetailedSessionAnalysis,
    ) -> AtlasWorkoutExecutionMatch:
        """Rapproche une activité et une séance du calendrier."""
        planned_workout.validate()

        date_difference = abs(
            (
                activity.start_time.date()
                - planned_workout.workout_date
            ).days
        )

        date_score = self._date_score(date_difference)
        sport_score = self._sport_score(
            planned_workout.sport,
            activity.activity_type,
        )
        duration_score = self._ratio_score(
            activity.duration_minutes,
            planned_workout.estimated_duration_minutes,
        )
        distance_score = self._optional_ratio_score(
            activity.distance_km,
            planned_workout.planned_distance_km,
        )
        expected_types = self._expected_execution_types(
            planned_workout
        )
        target_score = self._target_compliance(
            planned_workout.blocks,
            activity,
            analysis,
            expected_types=expected_types,
        )
        planned_intervals = self._planned_intervals(planned_workout)
        aligned_intervals = self._aligned_intervals(
            planned_intervals,
            analysis.blocks,
            expected_types,
            activity=activity,
        )
        if aligned_intervals:
            aligned_target_scores: list[tuple[int, float]] = []
            for item in aligned_intervals:
                planned_item = planned_intervals[int(item["planned_index"])]
                duration = max(1.0, float(item["duration_seconds"] or 0))
                score = self._block_target_score(
                    planned_item["planned"], SimpleNamespace(**item)
                )
                aligned_target_scores.append((score, duration))
            target_score = round(
                sum(score * duration for score, duration in aligned_target_scores)
                / sum(duration for _, duration in aligned_target_scores)
            )
        planned_recovery_minutes = sum(
            float(item["recovery_minutes"] or 0.0)
            for item in planned_intervals[:-1]
        )
        recovery_score = None
        if planned_recovery_minutes > 0:
            structured_recovery_score = (
                analysis.workout_execution.recovery_compliance_score
                if activity.workout_steps
                and analysis.workout_execution.planned_repetition_count > 0
                else None
            )
            if structured_recovery_score is not None:
                # Le FIT connaît les limites exactes de chaque récupération,
                # y compris après une répétition facultative. Sa comparaison
                # étape par étape est plus juste qu'un ratio avec le volume
                # minimal prévu dans le calendrier Atlas.
                recovery_score = structured_recovery_score
            else:
                aligned_recoveries = [
                    item["recovery_seconds"]
                    for item in aligned_intervals[:-1]
                    if item["recovery_seconds"] is not None
                ]
                if aligned_recoveries:
                    recovery_score = round(sum(
                        self._ratio_score(
                            actual / 60.0,
                            float(planned_intervals[index]["recovery_minutes"]),
                        )
                        for index, actual in enumerate(aligned_recoveries)
                        if float(planned_intervals[index]["recovery_minutes"] or 0) > 0
                    ) / len(aligned_recoveries))
                else:
                    recovery_score = self._ratio_score(
                        analysis.recovery_duration_seconds / 60.0,
                        planned_recovery_minutes,
                    )

        matching_scores = [
            (date_score, 50),
            (sport_score, 20),
            (duration_score, 15),
        ]
        if distance_score is not None:
            matching_scores.append((distance_score, 15))

        match_confidence = self._weighted_score(
            matching_scores
        )
        matched = (
            match_confidence >= self.MATCH_THRESHOLD
        )

        execution_scores = [
            (duration_score, 30),
            (target_score, 40),
        ]
        if distance_score is not None:
            execution_scores.append((distance_score, 30))
        if recovery_score is not None:
            execution_scores = [
                (score, round(weight * 0.85))
                for score, weight in execution_scores
            ]
            execution_scores.append((recovery_score, 15))

        execution_score = self._weighted_score(
            execution_scores
        )

        planned_active_blocks = [
            block
            for block in planned_workout.blocks
            if block.block_type
            not in {
                BlockType.WARM_UP,
                BlockType.RECOVERY,
                BlockType.COOL_DOWN,
            }
        ]
        work_blocks = [
            block
            for block in planned_active_blocks
            if block.block_type == BlockType.WORK
        ]
        repetition_blocks = (
            work_blocks
            if work_blocks
            else planned_active_blocks
        )
        planned_repetitions = sum(
            block.repetitions
            for block in repetition_blocks
        )
        executed_active_blocks = [
            block
            for block in analysis.blocks
            if block.block_type
            not in {"recovery", "warm_up", "cool_down"}
            and (
                expected_types is None
                or block.block_type in expected_types
            )
        ]

        reasons = [
            (
                f"Écart de date : "
                f"{date_difference} jour(s)."
            ),
            (
                f"Compatibilité du sport : "
                f"{sport_score}/100."
            ),
            (
                f"Respect de la durée : "
                f"{duration_score}/100."
            ),
            (
                f"Respect des cibles : "
                f"{target_score}/100."
            ),
        ]

        if distance_score is not None:
            reasons.append(
                f"Respect de la distance : "
                f"{distance_score}/100."
            )
        if recovery_score is not None:
            reasons.append(
                "Respect des récupérations : "
                f"{recovery_score}/100."
            )
            if recovery_score < 70:
                reasons.append(
                    "Une ou plusieurs récupérations semblent écourtées."
                )

        if not matched:
            reasons.append(
                "Correspondance insuffisante pour "
                "apprendre automatiquement."
            )

        structured_execution = analysis.workout_execution
        if aligned_intervals:
            completed_repetitions = len(aligned_intervals)
        elif (
            activity.workout_steps
            and structured_execution.planned_repetition_count > 0
        ):
            completed_repetitions = min(
                planned_repetitions,
                structured_execution.completed_repetition_count,
            )
        else:
            completed_repetitions = min(
                planned_repetitions,
                len(executed_active_blocks),
            )

        execution = WorkoutExecutionSummary(
            workout_name=planned_workout.title,
            workout_origin="atlas",
            origin_confidence_score=match_confidence,
            origin_reasons=reasons.copy(),
            planned_step_count=len(
                planned_workout.blocks
            ),
            executed_block_count=len(analysis.blocks),
            planned_repetition_count=planned_repetitions,
            completed_repetition_count=completed_repetitions,
            target_compliance_score=target_score,
            recovery_compliance_score=recovery_score,
            execution_score=execution_score,
            observations=reasons.copy(),
            interval_details=aligned_intervals,
        )

        return AtlasWorkoutExecutionMatch(
            workout_id=planned_workout.workout_id,
            activity_id=activity.atlas_id,
            matched=matched,
            match_confidence_score=match_confidence,
            execution=execution,
            date_difference_days=date_difference,
            duration_compliance_score=duration_score,
            distance_compliance_score=distance_score,
            target_compliance_score=target_score,
            physiological_load_score=(
                analysis.physiological_load_score
            ),
            biomechanical_load_score=(
                analysis.biomechanical_load_score
            ),
            reasons=reasons,
        )

    @staticmethod
    def _planned_intervals(
        planned_workout: AdaptiveWorkout,
    ) -> list[dict[str, object]]:
        """Déplie tous les paliers de travail, même s'ils diffèrent."""
        intervals: list[dict[str, object]] = []
        work_blocks = [
            block for block in planned_workout.blocks
            if block.block_type == BlockType.WORK
        ]
        for block_index, block in enumerate(work_blocks):
            for _ in range(max(1, int(block.repetitions or 1))):
                intervals.append({
                    "duration_seconds": (
                        float(block.duration_minutes) * 60
                        if block.duration_minutes is not None else None
                    ),
                    "distance_meters": block.distance_meters,
                    "recovery_minutes": block.recovery_minutes or 0.0,
                    "planned": block,
                })
            optional_text = (
                f"{block.name} {block.instructions} "
                f"{planned_workout.title if block_index == len(work_blocks) - 1 else ''}"
            ).lower()
            if (
                "facultative" in optional_text
                and ("seconde" in optional_text or "1 à 2" in optional_text)
            ):
                intervals.append({
                    "duration_seconds": (
                        float(block.duration_minutes) * 60
                        if block.duration_minutes is not None else None
                    ),
                    "distance_meters": block.distance_meters,
                    "recovery_minutes": block.recovery_minutes or 0.0,
                    "planned": block,
                    "optional": True,
                })
        return intervals

    @classmethod
    def _aligned_intervals(
        cls,
        planned: list[dict[str, object]],
        blocks: list[object],
        expected_types: set[str] | None,
        *,
        activity: LongitudinalActivity | None = None,
    ) -> list[dict[str, object]]:
        """Aligne une pyramide sur les groupes rapides dans leur ordre réel."""
        if not planned or not expected_types:
            return []

        groups = cls._raw_speed_interval_groups(planned, activity)
        if groups:
            return cls._align_interval_groups(planned, groups, blocks=[])

        groups: list[dict[str, object]] = []
        current: list[tuple[int, object]] = []

        def finish() -> None:
            if not current:
                return
            duration = sum(float(item.duration_seconds) for _, item in current)
            distance = sum(float(item.distance_meters) for _, item in current)
            speed_items = [
                item for _, item in current
                if item.average_speed_kmh is not None
            ]
            weighted_speed = (
                sum(
                    float(item.average_speed_kmh) * float(item.duration_seconds)
                    for item in speed_items
                ) / sum(float(item.duration_seconds) for item in speed_items)
                if speed_items else None
            )
            heart_values = [
                float(item.average_heart_rate_bpm)
                for _, item in current
                if item.average_heart_rate_bpm is not None
            ]
            groups.append({
                "start": current[0][0],
                "end": current[-1][0],
                "block_type": str(current[0][1].block_type),
                "duration_seconds": duration,
                "distance_meters": distance,
                "average_speed_kmh": weighted_speed,
                "average_heart_rate_bpm": (
                    sum(heart_values) / len(heart_values) if heart_values else None
                ),
                "maximum_heart_rate_bpm": max(
                    (float(item.maximum_heart_rate_bpm) for _, item in current
                     if item.maximum_heart_rate_bpm is not None),
                    default=None,
                ),
            })
            current.clear()

        for index, block in enumerate(blocks):
            if str(block.block_type) in expected_types:
                current.append((index, block))
            else:
                finish()
        finish()
        if not groups:
            return []

        return cls._align_interval_groups(planned, groups, blocks=blocks)

    @classmethod
    def _align_interval_groups(
        cls,
        planned: list[dict[str, object]],
        groups: list[dict[str, object]],
        *,
        blocks: list[object],
    ) -> list[dict[str, object]]:
        """Sélectionne les groupes compatibles avec les paliers prescrits."""
        # Programmation dynamique : conserve l'ordre, mais peut ignorer un
        # faux fragment rapide avant ou entre deux véritables fractions.
        memo: dict[tuple[int, int], tuple[float, list[tuple[int, int]]]] = {}

        def solve(pi: int, gi: int) -> tuple[float, list[tuple[int, int]]]:
            key = (pi, gi)
            if key in memo:
                return memo[key]
            if pi >= len(planned):
                return (0.0, [])
            if gi >= len(groups):
                return (4.0 * (len(planned) - pi), [])
            expected = planned[pi]
            actual = groups[gi]
            duration_target = expected["duration_seconds"]
            if duration_target:
                duration_cost = abs(
                    float(actual["duration_seconds"]) - float(duration_target)
                ) / float(duration_target)
            else:
                target_distance = float(expected["distance_meters"] or 1)
                duration_cost = abs(
                    float(actual["distance_meters"]) - target_distance
                ) / target_distance
            target_score = cls._block_target_score(
                expected["planned"], SimpleNamespace(**actual)
            )
            match_cost, match_pairs = solve(pi + 1, gi + 1)
            match = (duration_cost + (100 - target_score) / 100 + match_cost,
                     [(pi, gi), *match_pairs])
            skip_cost, skip_pairs = solve(pi, gi + 1)
            skip = (0.35 + skip_cost, skip_pairs)
            memo[key] = min(match, skip, key=lambda item: item[0])
            return memo[key]

        _, pairs = solve(0, 0)
        details: list[dict[str, object]] = []
        for pair_index, (planned_index, group_index) in enumerate(pairs):
            group = groups[group_index]
            planned_duration = planned[planned_index]["duration_seconds"]
            reported_duration = float(group["duration_seconds"])
            if (
                planned_duration is not None
                and abs(reported_duration - float(planned_duration)) <= 35
            ):
                reported_duration = float(planned_duration)
            reported_distance = (
                float(group["average_speed_kmh"]) / 3.6 * reported_duration
                if group.get("average_speed_kmh") is not None
                else float(group["distance_meters"])
            )
            next_start = (
                groups[pairs[pair_index + 1][1]]["start"]
                if pair_index + 1 < len(pairs) else None
            )
            recovery_seconds = None
            if group.get("raw_recovery_seconds") is not None:
                recovery_seconds = float(group["raw_recovery_seconds"])
            elif next_start is not None and blocks:
                recovery_seconds = sum(
                    float(blocks[index].duration_seconds)
                    for index in range(int(group["end"]) + 1, int(next_start))
                    if str(blocks[index].block_type) == "recovery"
                )
            details.append({
                key: value for key, value in {
                    "planned_index": planned_index,
                    "planned_duration_seconds": planned_duration,
                    "block_type": group["block_type"],
                    "duration_seconds": reported_duration,
                    "distance_meters": reported_distance,
                    "average_speed_kmh": group["average_speed_kmh"],
                    "average_heart_rate_bpm": group["average_heart_rate_bpm"],
                    "maximum_heart_rate_bpm": group["maximum_heart_rate_bpm"],
                    "recovery_seconds": recovery_seconds,
                }.items()
            })
        return details

    @classmethod
    def _raw_speed_interval_groups(
        cls,
        planned: list[dict[str, object]],
        activity: LongitudinalActivity | None,
    ) -> list[dict[str, object]]:
        """Reconstruit les fractions hétérogènes depuis la vitesse brute."""
        if activity is None or not activity.samples:
            return []
        durations = {
            round(float(item["duration_seconds"] or 0))
            for item in planned
            if item["duration_seconds"]
        }
        if len(durations) < 2:
            return []
        minimum_targets = [
            float(item["planned"].target.speed_min_kmh)
            for item in planned
            if item["planned"].target.speed_min_kmh is not None
        ]
        def timestamp(value: object) -> float:
            if hasattr(value, "timestamp"):
                return float(value.timestamp())
            from datetime import datetime
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            ).timestamp()

        speed_samples = sorted(
            (
                timestamp(sample.timestamp),
                float(sample.speed_mps) * 3.6,
            )
            for sample in activity.samples
            if sample.speed_mps is not None
        )
        if len(speed_samples) < 2:
            return []
        if minimum_targets:
            threshold_kmh = min(minimum_targets) * 0.85
        else:
            speeds = sorted(speed for _, speed in speed_samples if speed > 0)
            median_speed = speeds[len(speeds) // 2]
            fast_speed = speeds[min(len(speeds) - 1, round(len(speeds) * 0.90))]
            threshold_kmh = median_speed + (fast_speed - median_speed) * 0.40
        session_start = speed_samples[0][0]
        runs: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for sample_time, speed in speed_samples:
            if speed >= threshold_kmh:
                if current and sample_time - current[-1][0] > 25:
                    runs.append(current)
                    current = []
                current.append((sample_time, speed))
            elif current:
                runs.append(current)
                current = []
        if current:
            runs.append(current)

        groups: list[dict[str, object]] = []
        for run in runs:
            if len(run) < 3:
                continue
            observed_duration = run[-1][0] - run[0][0]
            if observed_duration < 45:
                continue
            closest_duration = min(
                durations,
                key=lambda value: abs(value - observed_duration),
            )
            if abs(closest_duration - observed_duration) > 35:
                continue
            average_speed = sum(speed for _, speed in run) / len(run)
            start_time, end_time = run[0][0], run[-1][0]
            heart_rates = [
                float(sample.heart_rate_bpm)
                for sample in activity.samples
                if sample.heart_rate_bpm is not None
                and start_time <= timestamp(sample.timestamp) <= end_time
            ]
            groups.append({
                "start": round(start_time - session_start),
                "end": round(end_time - session_start),
                "block_type": "vma",
                "duration_seconds": float(observed_duration),
                "distance_meters": average_speed / 3.6 * observed_duration,
                "average_speed_kmh": average_speed,
                "average_heart_rate_bpm": (
                    sum(heart_rates) / len(heart_rates) if heart_rates else None
                ),
                "maximum_heart_rate_bpm": max(heart_rates, default=None),
            })
        for left, right in zip(groups, groups[1:]):
            left["raw_recovery_seconds"] = max(
                0.0,
                float(right["start"]) - float(left["end"]),
            )
        return groups

    @staticmethod
    def _expected_execution_types(
        planned_workout: AdaptiveWorkout,
    ) -> set[str] | None:
        """Types FIT correspondant au travail principal prévu."""

        workout_type = getattr(
            planned_workout.workout_type,
            "value",
            planned_workout.workout_type,
        )
        repeated_work = [
            block
            for block in planned_workout.blocks
            if (
                block.block_type == BlockType.WORK
                and int(block.repetitions or 1) > 1
            )
        ]
        if (
            str(workout_type) == WorkoutType.LONG_RUN.value
            and repeated_work
        ):
            # Une sortie longue hybride reste une sortie longue pour le
            # calendrier, mais sa cible spécifique est portée par les
            # fractions répétées. Le footing facile ne doit donc pas être
            # évalué comme s'il devait atteindre l'allure sous SV2.
            return {"z3", "sv2"}

        mapping = {
            WorkoutType.RECOVERY_RUN.value: {"z1"},
            WorkoutType.ENDURANCE_Z2.value: {"z2"},
            WorkoutType.TEMPO_Z3.value: {"z3"},
            # Une fraction contrôlée peut être classée dans la zone
            # immédiatement inférieure lorsque l'allure est correcte mais
            # que la FC monte progressivement. Le footing facile ajouté
            # avant/après la série ne doit en revanche pas dégrader la note.
            WorkoutType.THRESHOLD_SV2.value: {"z3", "sv2"},
            WorkoutType.VMA_SHORT.value: {"sv2", "vma"},
            WorkoutType.VMA_LONG.value: {"sv2", "vma"},
            WorkoutType.HILL_SPRINTS.value: {
                "acceleration",
                "sprint",
            },
            WorkoutType.MIXED_THRESHOLD_VO2.value: {
                "sv2",
                "vma",
            },
            WorkoutType.TRIANGULAR_VO2.value: {
                "z3",
                "sv2",
                "vma",
            },
            WorkoutType.RACE_SPECIFIC.value: {
                "z3",
                "sv2",
            },
            WorkoutType.LONG_RUN.value: {"z2", "z3"},
        }
        return mapping.get(str(workout_type))
    def _target_compliance(
        self,
        planned_blocks: list[TrainingBlock],
        activity: LongitudinalActivity,
        analysis: DetailedSessionAnalysis,
        *,
        expected_types: set[str] | None = None,
    ) -> int:
        planned_active = [
            block
            for block in planned_blocks
            if (
                block.target.zone is not None
                or block.target.speed_min_kmh is not None
                or block.target.heart_rate_min_bpm is not None
            )
        ]

        if not planned_active:
            return 50

        if (
            len(planned_active) == 1
            and planned_active[0].block_type.value == "continuous"
        ):
            return self._continuous_target_score(
                planned_active[0],
                activity,
                analysis,
            )

        repeated_planned = [
            block
            for block in planned_active
            if (
                block.block_type == BlockType.WORK
                and int(block.repetitions or 1) > 1
            )
        ]
        target_blocks = repeated_planned or planned_active

        actual_blocks = [
            block
            for block in analysis.blocks
            if block.block_type
            not in {"recovery", "warm_up", "cool_down"}
            and (
                expected_types is None
                or block.block_type in expected_types
            )
        ]
        if not actual_blocks:
            return 50

        weighted_scores = []
        total_duration = 0.0

        for actual in actual_blocks:
            score = max(
                self._block_target_score(
                    planned,
                    actual,
                )
                for planned in target_blocks
            )
            duration = max(
                1.0,
                float(
                    getattr(
                        actual,
                        "duration_seconds",
                        1.0,
                    )
                    or 1.0
                ),
            )
            weighted_scores.append(score * duration)
            total_duration += duration

        return round(
            sum(weighted_scores) / total_duration
        )

    def _continuous_target_score(
        self,
        planned: TrainingBlock,
        activity: LongitudinalActivity,
        analysis: DetailedSessionAnalysis,
    ) -> int:
        """Évalue une séance continue sur sa réponse globale."""
        target = planned.target
        weighted_scores: list[tuple[int, int]] = []

        heart_rate = activity.average_heart_rate_bpm
        if (
            heart_rate is not None
            and target.heart_rate_min_bpm is not None
            and target.heart_rate_max_bpm is not None
        ):
            weighted_scores.append((
                self._range_score(
                    heart_rate,
                    target.heart_rate_min_bpm,
                    target.heart_rate_max_bpm,
                ),
                65,
            ))

        speed = activity.average_speed_kmh
        if (
            speed is not None
            and target.speed_min_kmh is not None
            and target.speed_max_kmh is not None
        ):
            weighted_scores.append((
                self._range_score(
                    speed,
                    target.speed_min_kmh,
                    target.speed_max_kmh,
                ),
                35,
            ))

        if not weighted_scores and target.zone is not None:
            if analysis.dominant_work_type == "cycling":
                # Une sortie vélo facultative ne doit pas être comparée aux
                # vitesses ni aux zones VMA de course à pied.
                return 85 if target.zone == 1 else 70
            expected_type = f"z{target.zone}"
            return (
                100
                if analysis.dominant_work_type == expected_type
                else 50
            )

        if not weighted_scores:
            return 50

        total_weight = sum(
            weight
            for _, weight in weighted_scores
        )
        return round(
            sum(
                score * weight
                for score, weight in weighted_scores
            )
            / total_weight
        )

    @classmethod
    def _block_target_score(
        cls,
        planned: TrainingBlock,
        actual: object,
    ) -> int:
        target = planned.target
        scores: list[int] = []

        speed = getattr(
            actual,
            "average_speed_kmh",
            None,
        )
        if (
            speed is not None
            and target.speed_min_kmh is not None
            and target.speed_max_kmh is not None
        ):
            scores.append(
                cls._range_score(
                    speed,
                    target.speed_min_kmh,
                    target.speed_max_kmh,
                )
            )

        heart_rate = getattr(
            actual,
            "average_heart_rate_bpm",
            None,
        )
        if (
            heart_rate is not None
            and target.heart_rate_min_bpm is not None
            and target.heart_rate_max_bpm is not None
        ):
            scores.append(
                cls._range_score(
                    heart_rate,
                    target.heart_rate_min_bpm,
                    target.heart_rate_max_bpm,
                )
            )

        if not scores and target.zone is not None:
            expected_type = f"z{target.zone}"
            scores.append(
                100
                if getattr(
                    actual,
                    "block_type",
                    "",
                ) == expected_type
                else 0
            )

        if not scores:
            return 50

        return round(sum(scores) / len(scores))

    @staticmethod
    def _range_score(
        value: float,
        minimum: float,
        maximum: float,
    ) -> int:
        """Accorde une tolérance progressive autour d'une cible."""
        if minimum <= value <= maximum:
            return 100

        difference = (
            minimum - value
            if value < minimum
            else value - maximum
        )
        width = max(1.0, maximum - minimum)
        relative_difference = difference / width

        if relative_difference <= 0.25:
            return 85
        if relative_difference <= 0.50:
            return 65
        if relative_difference <= 1.00:
            return 35
        return 0
    @staticmethod
    def _date_score(difference_days: int) -> int:
        if difference_days == 0:
            return 100
        if difference_days == 1:
            return 75
        if difference_days == 2:
            return 45
        return 0

    @staticmethod
    def _sport_score(
        planned_sport: str,
        actual_sport: str,
    ) -> int:
        planned = planned_sport.strip().lower()
        actual = actual_sport.strip().lower()

        running_aliases = {
            "running",
            "run",
            "course",
            "course à pied",
        }
        cycling_aliases = {
            "cycling",
            "cyclisme",
            "bike",
            "biking",
            "road",
            "vtt",
            "mountain_biking",
            "gravel_cycling",
        }

        if planned == actual:
            return 100
        if (
            planned in running_aliases
            and actual in running_aliases
        ):
            return 100
        if (
            planned in cycling_aliases
            and actual in cycling_aliases
        ):
            return 100
        return 0

    @classmethod
    def _optional_ratio_score(
        cls,
        actual: Optional[float],
        planned: Optional[float],
    ) -> Optional[int]:
        if (
            actual is None
            or planned is None
            or planned <= 0
        ):
            return None
        return cls._ratio_score(actual, planned)

    @staticmethod
    def _ratio_score(
        actual: float,
        planned: float,
    ) -> int:
        if planned <= 0:
            return 0

        difference_ratio = abs(actual - planned) / planned
        return max(
            0,
            min(
                100,
                round(100 - difference_ratio * 100),
            ),
        )

    @staticmethod
    def _weighted_score(
        values: list[tuple[int, int]],
    ) -> int:
        total_weight = sum(weight for _, weight in values)
        if total_weight <= 0:
            return 0

        return round(
            sum(
                score * weight
                for score, weight in values
            )
            / total_weight
        )
