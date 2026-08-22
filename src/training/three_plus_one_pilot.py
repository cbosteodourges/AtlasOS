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
    SUBTHRESHOLD_ROTATION = (
        ("subthreshold_3x10", "Sortie longue hybride · 3 × 10 min sous SV2", 30),
        ("subthreshold_5x6", "Sortie longue hybride · 5 × 6 min sous SV2", 30),
        ("subthreshold_8_to_10x3", "Sortie longue hybride · 8 × 3 min sous SV2", 24),
    )
    THRESHOLD_ROTATION = (
        ("SV2 raccourci · 3 × 1000 m", 15),
        ("SV2 raccourci · 2 × 8 min", 16),
        ("SV2 raccourci · 3 × 6 min", 18),
    )

    def build(
        self,
        *,
        start_date: date,
        wellness_status: str = "green",
        goal_surface: str = "road",
        downhill_experience: bool = False,
    ) -> ThreePlusOnePilotPlan:
        wellness = wellness_status.strip().lower()
        if wellness not in {"green", "orange", "red"}:
            raise ValueError("wellness_status doit être green, orange ou red.")
        surface = goal_surface.strip().lower()
        if surface not in {"road", "trail"}:
            raise ValueError("goal_surface doit être road ou trail.")

        monday = start_date - timedelta(days=start_date.weekday())
        weeks = [
            self._stimulus_week(monday + timedelta(weeks=index), index + 1, wellness)
            for index in range(3)
        ]
        weeks.append(
            self._consolidation_week(
                monday + timedelta(weeks=3),
                wellness,
                surface,
                downhill_experience,
            )
        )
        warnings = [
            "Pilote Atlas Research : le programme actif reste inchangé.",
            "Ne jamais augmenter simultanément l'allure et le volume spécifique.",
            "Toute douleur localisée ou récupération rouge remplace les stimuli par du facile.",
        ]
        if surface == "road":
            warnings.append("Le travail en descente reste désactivé pour l'objectif route.")
        return ThreePlusOnePilotPlan(
            start_date=monday,
            wellness_status=wellness,
            goal_surface=surface,
            specific_minutes_cap=self.SPECIFIC_MINUTES_CAP,
            weeks=weeks,
            warnings=warnings,
        )

    def _stimulus_week(self, monday: date, number: int, wellness: str) -> PilotWeek:
        threshold_title, threshold_minutes = self.THRESHOLD_ROTATION[number - 1]
        protocol_id, hybrid_title, subthreshold_minutes = self.SUBTHRESHOLD_ROTATION[number - 1]
        sessions = [
            PilotSession(monday, "easy", "Endurance fondamentale Z2", 45),
            PilotSession(
                monday + timedelta(days=1),
                "vo2_short",
                "VO₂max raccourcie · 6 × 400 m",
                48,
                specific_minutes=12,
                is_specific=True,
                is_metabolic=True,
                instructions=["Régularité prioritaire ; aucune répétition sprintée."],
            ),
            PilotSession(
                monday + timedelta(days=3),
                "threshold_short",
                threshold_title,
                50,
                specific_minutes=threshold_minutes,
                is_specific=True,
                is_metabolic=True,
                instructions=["Rester autour ou légèrement sous le SV2 longitudinal."],
            ),
            PilotSession(
                monday + timedelta(days=5),
                "hybrid_long_subthreshold",
                hybrid_title,
                80,
                specific_minutes=subthreshold_minutes,
                is_specific=True,
                is_metabolic=True,
                protocol_id=protocol_id,
                instructions=[
                    "Cette séance n'est pas un test.",
                    "RPE 5–6/10 et sensation de pouvoir effectuer une répétition supplémentaire.",
                    "Ralentir si la FC reste proche ou au-dessus du SV2.",
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
                    item.duration_minutes = round(item.duration_minutes * 0.9)
                    item.volume_factor = 0.75
                    item.instructions.append("Volume spécifique réduit de 25 % par Atlas Wellness.")
        elif wellness == "red":
            sessions = self._replace_with_easy(sessions)

        specific = sum(item.specific_minutes for item in sessions)
        if specific > self.SPECIFIC_MINUTES_CAP:
            raise ValueError("Le plafond hebdomadaire de minutes spécifiques est dépassé.")
        return PilotWeek(number, monday, sessions)

    def _consolidation_week(
        self,
        monday: date,
        wellness: str,
        surface: str,
        downhill_experience: bool,
    ) -> PilotWeek:
        sessions = [
            PilotSession(monday, "easy", "Endurance facile", 35),
            PilotSession(
                monday + timedelta(days=1),
                "easy_hill_microdose",
                "Endurance + microdose côte · 6 à 8 répétitions",
                40,
                protocol_id="hill_neuromuscular_sprints",
                instructions=[
                    "Première exposition : 6 × 12 s, pente 4–7 %, récupération complète 2 min 30.",
                    "Passer à 7 puis 8 seulement si technique, douleur et récupération à J+1 sont favorables.",
                ],
            ),
            PilotSession(monday + timedelta(days=3), "easy", "Endurance facile", 35),
            PilotSession(
                monday + timedelta(days=4),
                "easy_flat_microdose",
                "Endurance + lignes droites · 6 à 8 répétitions",
                40,
                protocol_id="flat_relaxed_strides",
                instructions=[
                    "Première exposition : 6 × 20 s à 85–92 %, récupération complète 2 min.",
                    "Progresser vers 7 puis 8 répétitions sans augmenter simultanément la vitesse.",
                ],
            ),
            PilotSession(
                monday + timedelta(days=6),
                "recovery_cycling",
                "Vélo facile facultatif",
                60,
                optional=True,
            ),
        ]
        if surface == "trail" and downhill_experience and wellness == "green":
            sessions[3] = PilotSession(
                monday + timedelta(days=4),
                "easy_downhill_microdose",
                "Endurance + introduction descente douce",
                40,
                protocol_id="gentle_downhill_eccentric_intro",
                instructions=["4 × 12 s, pente 2–3 %, surface sèche, vitesse non maximale."],
            )
        if wellness == "red":
            sessions = self._replace_with_easy(sessions)
        return PilotWeek(
            week_number=4,
            start_date=monday,
            sessions=sessions,
            volume_factor=0.70,
            is_consolidation=True,
        )

    @staticmethod
    def _replace_with_easy(sessions: list[PilotSession]) -> list[PilotSession]:
        replaced = []
        for item in sessions:
            if item.is_specific or item.protocol_id:
                replaced.append(PilotSession(
                    workout_date=item.workout_date,
                    session_key="wellness_replacement",
                    title="Endurance facile adaptée par Atlas Wellness",
                    duration_minutes=min(40, item.duration_minutes),
                    instructions=["Stimulus supprimé : récupération rouge ou données défavorables."],
                ))
            else:
                replaced.append(item)
        return replaced


def compare_with_active_program(
    active_program: dict[str, object],
    pilot: ThreePlusOnePilotPlan,
) -> dict[str, object]:
    """Compare sans mutation les quatre semaines du plan actif au pilote."""
    active_copy = deepcopy(active_program)
    window_start = pilot.start_date
    window_end = window_start + timedelta(days=27)
    specific_types = {
        "tempo_z3",
        "threshold_sv2",
        "vma_short",
        "vma_long",
        "mixed_threshold_vo2",
        "triangular_vo2",
        "race_specific",
    }
    active_weeks = []
    for week in active_copy.get("weeks", []):
        sessions = []
        for workout in week.get("workouts", []):
            raw_day = workout.get("workout_date")
            try:
                workout_day = date.fromisoformat(str(raw_day)[:10])
            except (TypeError, ValueError):
                continue
            if not window_start <= workout_day <= window_end:
                continue
            workout_type = str(workout.get("workout_type") or "")
            sessions.append({
                "date": workout_day.isoformat(),
                "title": workout.get("title"),
                "workout_type": workout_type,
                "is_specific": workout_type in specific_types,
                "duration_minutes": workout.get("planned_duration_minutes"),
            })
        if sessions:
            active_weeks.append({
                "week_number": week.get("week_number"),
                "phase": week.get("phase"),
                "specific_session_count": sum(
                    item["is_specific"] for item in sessions
                ),
                "sessions": sessions,
            })
    return {
        "comparison_only": True,
        "active_program_unchanged": active_program == active_copy,
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
        },
        "active": {"weeks": active_weeks},
        "pilot": pilot.to_dict(),
        "activation": {
            "status": "not_activated",
            "message": "Validation utilisateur requise avant toute modification du programme actif.",
        },
    }
