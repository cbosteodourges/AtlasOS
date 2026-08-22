"""Prévisualisation isolée du cycle Atlas Research 3+1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from copy import deepcopy


@dataclass(slots=True)
class PilotSession:
    workout_date: date
    session_key: str
    title: str
    duration_minutes: int
    specific_minutes: float = 0
    specific_minutes_min: float = 0
    specific_minutes_max: float = 0
    repetitions_min: int | None = None
    repetitions_max: int | None = None
    is_specific: bool = False
    is_metabolic: bool = False
    protocol_id: str | None = None
    volume_factor: float = 1.0
    optional: bool = False
    instructions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["workout_date"] = self.workout_date.isoformat()
        return payload


@dataclass(slots=True)
class PilotWeek:
    week_number: int
    start_date: date
    sessions: list[PilotSession]
    volume_factor: float = 1.0
    is_consolidation: bool = False

    @property
    def specific_minutes(self) -> float:
        return round(sum(item.specific_minutes for item in self.sessions), 1)

    @property
    def specific_session_count(self) -> int:
        return sum(item.is_specific for item in self.sessions)

    @property
    def total_duration_minutes(self) -> int:
        return sum(item.duration_minutes for item in self.sessions)

    def to_dict(self) -> dict[str, object]:
        return {
            "week_number": self.week_number,
            "start_date": self.start_date.isoformat(),
            "is_consolidation": self.is_consolidation,
            "volume_factor": self.volume_factor,
            "specific_minutes": self.specific_minutes,
            "specific_session_count": self.specific_session_count,
            "total_duration_minutes": self.total_duration_minutes,
            "sessions": [item.to_dict() for item in self.sessions],
        }


@dataclass(slots=True)
class ThreePlusOnePilotPlan:
    start_date: date
    wellness_status: str
    goal_surface: str
    specific_minutes_cap: int
    weeks: list[PilotWeek]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "pilot": True,
            "activated": False,
            "periodization": "three_plus_one_multistimulus",
            "start_date": self.start_date.isoformat(),
            "wellness_status": self.wellness_status,
            "goal_surface": self.goal_surface,
            "specific_minutes_cap": self.specific_minutes_cap,
            "weeks": [item.to_dict() for item in self.weeks],
            "warnings": self.warnings,
        }


class ThreePlusOnePilotPlanner:
    """Construit une proposition comparative sans toucher au plan actif."""

    SPECIFIC_MINUTES_CAP = 60
    FLEXIBLE_PROGRESSIONS = (
        {
            "vo2": ("VO₂max contrôlée · 6 à 8 × 400 m", 11, 10, 13, 6, 8),
            "threshold": ("SV2 contrôlé · 3 à 4 × 1000 m", 17, 14, 19, 3, 4),
            "hybrid": ("Sortie longue hybride · 3 à 4 × 6 min sous SV2", 20, 18, 24, 3, 4),
        },
        {
            "vo2": ("VO₂max contrôlée · 6 à 8 × 400 m", 12, 10, 13, 6, 8),
            "threshold": ("SV2 contrôlé · 3 à 4 × 1200 m", 20, 17, 23, 3, 4),
            "hybrid": ("Sortie longue hybride · 3 à 4 × 6 min sous SV2", 23, 18, 24, 3, 4),
        },
        {
            "vo2": ("VO₂max contrôlée · 6 à 8 × 500 m", 15, 14, 17, 6, 8),
            "threshold": ("SV2 contrôlé · 4 à 5 × 1000 m", 21, 19, 23, 4, 5),
            "hybrid": ("Sortie longue hybride · 3 à 4 × 5 min sous SV2", 20, 15, 20, 3, 4),
        },
    )    def _stimulus_week(self, monday: date, number: int, wellness: str) -> PilotWeek:
        progression = self.FLEXIBLE_PROGRESSIONS[number - 1]
        vo2_title, vo2_planned, vo2_min, vo2_max, vo2_reps_min, vo2_reps_max = progression["vo2"]
        threshold_title, threshold_planned, threshold_min, threshold_max, threshold_reps_min, threshold_reps_max = progression["threshold"]
        hybrid_title, hybrid_planned, hybrid_min, hybrid_max, hybrid_reps_min, hybrid_reps_max = progression["hybrid"]
        autoregulation = [
            "Commencer par la borne basse : les répétitions supplémentaires sont facultatives.",
            "Arrêter en gardant la sensation de pouvoir effectuer encore une répétition propre.",
            "Ne pas poursuivre si la technique se dégrade, si une douleur apparaît ou si le RPE dépasse 7/10.",
        ]
        sessions = [
            PilotSession(monday, "easy", "Endurance fondamentale Z2", 45),
            PilotSession(
                monday + timedelta(days=1),
                "vo2_short",
                vo2_title,
                48 + (number - 1) * 2,
                specific_minutes=vo2_planned,
                specific_minutes_min=vo2_min,
                specific_minutes_max=vo2_max,
                repetitions_min=vo2_reps_min,
                repetitions_max=vo2_reps_max,
                is_specific=True,
                is_metabolic=True,
                instructions=[
                    "Régularité prioritaire ; aucune répétition sprintée.",
                    *autoregulation,
                ],
            ),
            PilotSession(
                monday + timedelta(days=3),
                "threshold_short",
                threshold_title,
                50 + (number - 1) * 2,
                specific_minutes=threshold_planned,
                specific_minutes_min=threshold_min,
                specific_minutes_max=threshold_max,
                repetitions_min=threshold_reps_min,
                repetitions_max=threshold_reps_max,
                is_specific=True,
                is_metabolic=True,
                instructions=[
                    "Rester autour ou légèrement sous le SV2 longitudinal.",
                    *autoregulation,
                ],
            ),
            PilotSession(
                monday + timedelta(days=5),
                "hybrid_long_subthreshold",
                hybrid_title,
                80 + (number - 1) * 3,
                specific_minutes=hybrid_planned,
                specific_minutes_min=hybrid_min,
                specific_minutes_max=hybrid_max,
                repetitions_min=hybrid_reps_min,
                repetitions_max=hybrid_reps_max,
                is_specific=True,
                is_metabolic=True,
                protocol_id="progressive_hybrid_subthreshold",
                instructions=[
                    "Cette séance n'est pas un test.",
                    "RPE 5–6/10 et sensation de pouvoir effectuer une répétition supplémentaire.",
                    "Ralentir si la FC reste proche ou au-dessus du SV2.",
                    *autoregulation,
                ],
            ),
            PilotSession(
                monday + timedelta(days=6),
                "recovery_cycling",
                "Vélo de récupération",
                75,
                instructions=["Faible résistance, FC Z1 ou bas Z2, sans accélération finale."],
            ),
        ]
        if wellness == "orange":
            for item in sessions:
                if item.is_specific:
                    item.specific_minutes = round(item.specific_minutes * 0.75, 1)
                    item.specific_minutes_min = round(item.specific_minutes_min * 0.75, 1)
                    item.specific_minutes_max = round(item.specific_minutes_max * 0.75, 1)
                    item.duration_minutes = round(item.duration_minutes * 0.9)
                    item.volume_factor = 0.75
                    item.instructions.append("Volume spécifique réduit de 25 % par Atlas Wellness.")
        elif wellness == "red":
            sessions = self._replace_with_easy(sessions)

        specific = sum(item.specific_minutes for item in sessions)
        maximum_specific = sum(item.specific_minutes_max for item in sessions)
        if specific > self.SPECIFIC_MINUTES_CAP or maximum_specific > self.SPECIFIC_MINUTES_CAP:
            raise ValueError("Le plafond hebdomadaire de minutes spécifiques est dépassé.")
        return PilotWeek(number, monday, sessions)

