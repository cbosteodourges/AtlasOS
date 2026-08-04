"""
ATLAS OS
Détection adaptative des périodes de préparation.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Dict, List, Optional, Tuple

from .competition_models import (
    AdaptivePreparationPeriod,
    CompetitionEvent,
    PreparationPhaseSummary,
)
from .longitudinal_models import LongitudinalActivity


class AdaptivePreparationAnalyzer:
    """
    Détecte la période de préparation réellement pertinente.

    Le moteur recherche une rupture entre l'entraînement
    habituel antérieur et une période récente plus dense,
    plus volumineuse ou plus spécifique.
    """

    MIN_HISTORY_DAYS = 42
    TAPER_DAYS = 7
    BASE_PHASE_RATIO = 0.55

    def detect(
        self,
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
    ) -> AdaptivePreparationPeriod:
        """Détecte et décrit la préparation précédant un événement."""
        running = sorted(
            [
                activity
                for activity in activities
                if (
                    self._is_running(activity)
                    and activity.start_time
                    < event.event_date
                )
            ],
            key=lambda activity: activity.start_time,
        )

        if not running:
            return self._empty_result(event)

        earliest = running[0].start_time
        available_history_days = max(
            (
                event.event_date.date()
                - earliest.date()
            ).days,
            1,
        )

        data_limited = (
            available_history_days
            < self.MIN_HISTORY_DAYS
        )
        reasons: List[str] = []
        change_week: Optional[int] = None

        if data_limited:
            detected_start = earliest
            reasons.append(
                "Historique disponible trop court pour "
                "identifier une rupture d'entraînement fiable."
            )
            reasons.append(
                "La première activité disponible est utilisée "
                "comme début provisoire de préparation."
            )
        else:
            weekly = self._weekly_metrics(
                running,
                event,
            )
            change_week = self._detect_change_week(
                weekly
            )

            if change_week is None:
                detected_start = earliest
                reasons.append(
                    "Aucune rupture d'entraînement suffisamment "
                    "nette n'a été détectée."
                )
                reasons.append(
                    "La première activité disponible est retenue "
                    "pour ne pas supprimer une phase utile."
                )
            else:
                detected_start = self._start_of_week(
                    running,
                    event,
                    change_week,
                )
                reasons.extend(
                    self._change_reasons(
                        weekly,
                        change_week,
                    )
                )

        duration_days = max(
            (
                event.event_date.date()
                - detected_start.date()
            ).days,
            1,
        )

        selected = [
            activity
            for activity in running
            if detected_start
            <= activity.start_time
            < event.event_date
        ]

        confidence = self._confidence_score(
            selected=selected,
            duration_days=duration_days,
            change_detected=(
                change_week is not None
            ),
            data_limited=data_limited,
        )

        phases = self._build_phases(
            selected,
            event,
            detected_start,
        )

        return AdaptivePreparationPeriod(
            event=event,
            detected_start_at=detected_start,
            detected_end_at=event.event_date,
            duration_days=duration_days,
            duration_weeks=round(
                duration_days / 7,
                1,
            ),
            available_history_days=(
                available_history_days
            ),
            available_history_weeks=round(
                available_history_days / 7,
                1,
            ),
            data_limited=data_limited,
            confidence_score=confidence,
            detection_reasons=reasons,
            phases=phases,
        )

    def _weekly_metrics(
        self,
        running: List[LongitudinalActivity],
        event: CompetitionEvent,
    ) -> Dict[int, Dict[str, float]]:
        """
        Regroupe les courses par semaine avant la compétition.

        La semaine 0 correspond aux sept derniers jours.
        La semaine 1 correspond aux jours 7 à 13, etc.
        """
        weekly: Dict[
            int,
            Dict[str, float],
        ] = defaultdict(
            lambda: {
                "sessions": 0.0,
                "distance": 0.0,
                "intensity": 0.0,
                "long_runs": 0.0,
                "quality_total": 0.0,
            }
        )

        for activity in running:
            days_before = (
                event.event_date.date()
                - activity.start_time.date()
            ).days

            if days_before <= 0:
                continue

            week_index = days_before // 7
            values = weekly[week_index]
            values["sessions"] += 1
            values["distance"] += (
                activity.distance_km
            )
            values["quality_total"] += (
                activity.data_quality_score
            )

            if self._is_intensity(activity):
                values["intensity"] += 1

            if self._is_long_run(
                activity,
                event,
            ):
                values["long_runs"] += 1

        return dict(weekly)

    def _detect_change_week(
        self,
        weekly: Dict[int, Dict[str, float]],
    ) -> Optional[int]:
        """
        Recherche la semaine où commence une hausse durable.

        Quatre semaines récentes sont comparées aux quatre
        semaines qui les précèdent. Le meilleur contraste
        cohérent est conservé.
        """
        if not weekly:
            return None

        maximum_week = max(weekly)
        candidates: List[
            Tuple[float, int]
        ] = []

        for change_week in range(
            4,
            maximum_week - 3,
        ):
            recent = self._period_average(
                weekly,
                range(
                    change_week - 3,
                    change_week + 1,
                ),
            )
            baseline = self._period_average(
                weekly,
                range(
                    change_week + 1,
                    change_week + 5,
                ),
            )

            frequency_gain = (
                recent["sessions"]
                - baseline["sessions"]
            )
            volume_gain = (
                recent["distance"]
                - baseline["distance"]
            )

            frequency_ratio = self._safe_ratio(
                recent["sessions"],
                baseline["sessions"],
            )
            volume_ratio = self._safe_ratio(
                recent["distance"],
                baseline["distance"],
            )

            denser = (
                frequency_gain >= 0.75
                or frequency_ratio >= 1.5
            )
            more_volume = (
                volume_gain >= 5.0
                or volume_ratio >= 1.4
            )
            structured = (
                recent["intensity"]
                > baseline["intensity"]
                or recent["long_runs"]
                > baseline["long_runs"]
            )

            if not (
                denser
                and more_volume
                and structured
            ):
                continue

            contrast_score = (
                min(frequency_ratio, 4.0) * 2
                + min(volume_ratio, 4.0) * 2
                + (
                    recent["intensity"]
                    - baseline["intensity"]
                )
                + (
                    recent["long_runs"]
                    - baseline["long_runs"]
                )
            )
            candidates.append(
                (
                    contrast_score,
                    change_week,
                )
            )

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: (
                item[0],
                -item[1],
            ),
        )[1]

    @staticmethod
    def _period_average(
        weekly: Dict[int, Dict[str, float]],
        week_indexes: range,
    ) -> Dict[str, float]:
        keys = (
            "sessions",
            "distance",
            "intensity",
            "long_runs",
        )

        return {
            key: mean(
                weekly.get(
                    week_index,
                    {},
                ).get(
                    key,
                    0.0,
                )
                for week_index in week_indexes
            )
            for key in keys
        }

    def _start_of_week(
        self,
        running: List[LongitudinalActivity],
        event: CompetitionEvent,
        week_index: int,
    ) -> datetime:
        lower_days = week_index * 7
        upper_days = lower_days + 6

        candidates = [
            activity.start_time
            for activity in running
            if lower_days
            <= (
                event.event_date.date()
                - activity.start_time.date()
            ).days
            <= upper_days
        ]

        if candidates:
            return min(candidates)

        return (
            event.event_date
            - timedelta(days=lower_days)
        )

    def _change_reasons(
        self,
        weekly: Dict[int, Dict[str, float]],
        change_week: int,
    ) -> List[str]:
        recent = self._period_average(
            weekly,
            range(
                change_week - 3,
                change_week + 1,
            ),
        )
        baseline = self._period_average(
            weekly,
            range(
                change_week + 1,
                change_week + 5,
            ),
        )

        reasons = [
            "Hausse durable de la fréquence des courses : "
            f"{baseline['sessions']:.1f} à "
            f"{recent['sessions']:.1f} séance(s) par semaine.",
            "Hausse durable du volume de course : "
            f"{baseline['distance']:.1f} à "
            f"{recent['distance']:.1f} km par semaine.",
        ]

        if (
            recent["intensity"]
            > baseline["intensity"]
        ):
            reasons.append(
                "Augmentation des séances d'intensité "
                "pendant la période détectée."
            )

        if (
            recent["long_runs"]
            > baseline["long_runs"]
        ):
            reasons.append(
                "Augmentation des sorties longues "
                "pendant la période détectée."
            )

        return reasons

    def _build_phases(
        self,
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
        detected_start: datetime,
    ) -> List[PreparationPhaseSummary]:
        duration_days = max(
            (
                event.event_date.date()
                - detected_start.date()
            ).days,
            1,
        )

        taper_days = min(
            self.TAPER_DAYS,
            max(duration_days // 3, 1),
        )
        preparation_days = max(
            duration_days - taper_days,
            2,
        )
        base_days = max(
            round(
                preparation_days
                * self.BASE_PHASE_RATIO
            ),
            1,
        )

        base_end = min(
            detected_start
            + timedelta(days=base_days),
            event.event_date,
        )
        taper_start = max(
            event.event_date
            - timedelta(days=taper_days),
            base_end,
        )

        return [
            self._summarize_phase(
                "base",
                detected_start,
                base_end,
                activities,
                event,
            ),
            self._summarize_phase(
                "specific",
                base_end,
                taper_start,
                activities,
                event,
            ),
            self._summarize_phase(
                "taper",
                taper_start,
                event.event_date,
                activities,
                event,
            ),
        ]

    def _summarize_phase(
        self,
        phase_name: str,
        start_at: datetime,
        end_at: datetime,
        activities: List[LongitudinalActivity],
        event: CompetitionEvent,
    ) -> PreparationPhaseSummary:
        selected = [
            activity
            for activity in activities
            if start_at
            <= activity.start_time
            < end_at
        ]
        duration_days = max(
            (
                end_at.date()
                - start_at.date()
            ).days,
            1,
        )
        distance = sum(
            activity.distance_km
            for activity in selected
        )

        return PreparationPhaseSummary(
            phase_name=phase_name,
            start_at=start_at,
            end_at=end_at,
            duration_days=duration_days,
            activity_count=len(selected),
            running_activity_count=len(selected),
            running_distance_km=round(
                distance,
                1,
            ),
            average_running_distance_per_week_km=round(
                distance
                / duration_days
                * 7,
                1,
            ),
            high_intensity_session_count=sum(
                self._is_intensity(activity)
                for activity in selected
            ),
            long_run_count=sum(
                self._is_long_run(
                    activity,
                    event,
                )
                for activity in selected
            ),
        )

    @staticmethod
    def _confidence_score(
        selected: List[LongitudinalActivity],
        duration_days: int,
        change_detected: bool,
        data_limited: bool,
    ) -> int:
        if data_limited:
            score = 25
        else:
            score = 45

        if change_detected:
            score += 25

        if duration_days >= 56:
            score += 10

        if len(selected) >= 20:
            score += 10

        quality_scores = [
            activity.data_quality_score
            for activity in selected
        ]

        if (
            quality_scores
            and mean(quality_scores) >= 70
        ):
            score += 10

        return min(score, 100)

    @staticmethod
    def _safe_ratio(
        current: float,
        previous: float,
    ) -> float:
        if previous <= 0:
            return (
                4.0
                if current > 0
                else 1.0
            )

        return current / previous

    def _empty_result(
        self,
        event: CompetitionEvent,
    ) -> AdaptivePreparationPeriod:
        start_at = (
            event.event_date
            - timedelta(days=1)
        )

        return AdaptivePreparationPeriod(
            event=event,
            detected_start_at=start_at,
            detected_end_at=event.event_date,
            duration_days=1,
            duration_weeks=0.1,
            available_history_days=0,
            available_history_weeks=0.0,
            data_limited=True,
            confidence_score=0,
            detection_reasons=[
                "Aucune activité de course antérieure "
                "à la compétition n'est disponible."
            ],
            phases=self._build_phases(
                [],
                event,
                start_at,
            ),
        )

    @staticmethod
    def _is_intensity(
        activity: LongitudinalActivity,
    ) -> bool:
        title = activity.title.lower()

        return any(
            keyword in title
            for keyword in {
                "seuil",
                "tempo",
                "vo2",
                "vma",
                "fraction",
                "interval",
            }
        ) or bool(
            re.search(
                r"\d+\s*x\s*\d+",
                title,
            )
        )

    @staticmethod
    def _is_long_run(
        activity: LongitudinalActivity,
        event: CompetitionEvent,
    ) -> bool:
        title = activity.title.lower()
        distance_threshold = max(
            12.0,
            event.distance_km * 0.65,
        )

        return (
            "longue course" in title
            or "sortie longue" in title
            or "long run" in title
            or activity.distance_km
            >= distance_threshold
        )

    @staticmethod
    def _is_running(
        activity: LongitudinalActivity,
    ) -> bool:
        activity_type = (
            activity.activity_type.lower()
        )

        return (
            "running" in activity_type
            or activity_type
            in {
                "ultrafond",
                "ultra_running",
            }
        )