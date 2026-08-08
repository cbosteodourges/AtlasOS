"""
ATLAS OS
Saisie quotidienne de récupération sans capteur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.physiology.physiology_engine import PhysiologyInput


@dataclass(slots=True)
class ManualRecoveryCheckIn:
    """Bilan quotidien réalisable en moins de 30 secondes."""

    day: date
    sleep_quality_0_10: Optional[float] = None
    fatigue_0_10: Optional[float] = None
    muscle_soreness_0_10: Optional[float] = None
    pain_0_10: Optional[float] = None
    stress_0_10: Optional[float] = None

    sleep_hours: Optional[float] = None
    illness_symptoms: Optional[bool] = None
    pain_locations: list[str] = field(
        default_factory=list
    )
    notes: str = ""

    source: str = "manual"

    def validate(self) -> None:
        for name in (
            "sleep_quality_0_10",
            "fatigue_0_10",
            "muscle_soreness_0_10",
            "pain_0_10",
            "stress_0_10",
        ):
            value = getattr(self, name)
            if value is not None and not 0 <= value <= 10:
                raise ValueError(
                    f"{name} doit être compris entre 0 et 10."
                )

        if (
            self.sleep_hours is not None
            and not 0 <= self.sleep_hours <= 16
        ):
            raise ValueError(
                "sleep_hours doit être compris entre 0 et 16."
            )

    @property
    def data_quality_score(self) -> int:
        """Qualité fondée sur les cinq réponses principales."""
        answered = sum(
            value is not None
            for value in (
                self.sleep_quality_0_10,
                self.fatigue_0_10,
                self.muscle_soreness_0_10,
                self.pain_0_10,
                self.stress_0_10,
            )
        )
        return answered * 20


class ManualRecoveryConnector:
    """Transforme le bilan manuel en entrée physiologique."""

    def build_input(
        self,
        check_in: ManualRecoveryCheckIn,
        *,
        sleep_need_hours: float = 8.0,
        acute_load_7d: Optional[float] = None,
        chronic_load_28d: Optional[float] = None,
        vo2max: Optional[float] = None,
        vo2max_baseline: Optional[float] = None,
    ) -> PhysiologyInput:
        """Construit une entrée sans exiger de montre connectée."""
        check_in.validate()

        notes = check_in.notes.strip()

        if check_in.pain_locations:
            locations = ", ".join(
                check_in.pain_locations
            )
            location_note = (
                f"Localisation(s) de douleur : {locations}."
            )
            notes = (
                f"{notes} {location_note}".strip()
            )

        return PhysiologyInput(
            sleep_hours=check_in.sleep_hours,
            sleep_need_hours=sleep_need_hours,
            sleep_quality_0_100=(
                None
                if check_in.sleep_quality_0_10 is None
                else check_in.sleep_quality_0_10 * 10.0
            ),
            stress_0_10=check_in.stress_0_10,
            subjective_fatigue_0_10=(
                check_in.fatigue_0_10
            ),
            muscle_soreness_0_10=(
                check_in.muscle_soreness_0_10
            ),
            acute_load_7d=acute_load_7d,
            chronic_load_28d=chronic_load_28d,
            vo2max=vo2max,
            vo2max_baseline=vo2max_baseline,
            pain_0_10=check_in.pain_0_10,
            illness_symptoms=bool(
                check_in.illness_symptoms
            ),
            notes=notes,
        )