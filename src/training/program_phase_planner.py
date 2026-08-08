"""Planification explicable des phases d’un programme Atlas Coach."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from math import ceil

from .program_models import TrainingPhase


@dataclass(slots=True)
class ProgramPhasePlan:
    """Répartition des phases jusqu’à l’objectif."""

    start_date: date
    event_date: date
    phases: list[TrainingPhase]
    foundation_ratio: float

    @property
    def duration_weeks(self) -> int:
        return len(self.phases)

    @property
    def phase_counts(self) -> dict[TrainingPhase, int]:
        return dict(Counter(self.phases))


class ProgramPhasePlanner:
    """Transforme le temps disponible en phases progressives."""

    FOUNDATION_RATIO = 0.55
    BASE_SHARE_OF_FOUNDATION = 2 / 3

    def plan(
        self,
        *,
        start_date: date,
        event_date: date,
    ) -> ProgramPhasePlan:
        """Construit une phase pour chaque semaine disponible."""
        if event_date < start_date:
            raise ValueError(
                "event_date ne peut pas précéder start_date."
            )

        duration_days = (
            event_date - start_date
        ).days + 1
        total_weeks = max(1, ceil(duration_days / 7))
        phases = self._build_phases(total_weeks)

        return ProgramPhasePlan(
            start_date=start_date,
            event_date=event_date,
            phases=phases,
            foundation_ratio=self.FOUNDATION_RATIO,
        )

    def _build_phases(
        self,
        total_weeks: int,
    ) -> list[TrainingPhase]:
        if total_weeks == 1:
            return [TrainingPhase.RACE_WEEK]

        if total_weeks == 2:
            return [
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            ]

        if total_weeks == 3:
            return [
                TrainingPhase.SPECIFIC,
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            ]

        if total_weeks == 4:
            return [
                TrainingPhase.DEVELOPMENT,
                TrainingPhase.SPECIFIC,
                TrainingPhase.TAPER,
                TrainingPhase.RACE_WEEK,
            ]

        productive_weeks = total_weeks - 2
        foundation_weeks = round(
            productive_weeks * self.FOUNDATION_RATIO
        )
        foundation_weeks = max(
            2,
            min(productive_weeks - 1, foundation_weeks),
        )
        base_weeks = round(
            foundation_weeks
            * self.BASE_SHARE_OF_FOUNDATION
        )
        base_weeks = max(
            1,
            min(foundation_weeks - 1, base_weeks),
        )
        development_weeks = foundation_weeks - base_weeks
        specific_weeks = (
            productive_weeks - foundation_weeks
        )

        return [
            *([TrainingPhase.BASE] * base_weeks),
            *(
                [TrainingPhase.DEVELOPMENT]
                * development_weeks
            ),
            *(
                [TrainingPhase.SPECIFIC]
                * specific_weeks
            ),
            TrainingPhase.TAPER,
            TrainingPhase.RACE_WEEK,
        ]