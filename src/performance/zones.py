"""
ATLAS OS
Calcul des zones d’entraînement.
"""

from typing import List, Optional

from src.performance.models import TrainingZone


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — OUTILS D’ALLURE
# ████████████████████████████████████████████████████████████

def speed_to_pace_seconds(
    speed_kmh: float,
) -> Optional[int]:
    if speed_kmh <= 0:
        return None

    return round(3600 / speed_kmh)


def format_pace(
    pace_seconds: Optional[int],
) -> str:
    if pace_seconds is None:
        return "—"

    minutes = pace_seconds // 60
    seconds = pace_seconds % 60

    return f"{minutes}'{seconds:02d}/km"


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — MOTEUR DE ZONES
# ████████████████████████████████████████████████████████████

class TrainingZonesEngine:
    ZONE_DEFINITIONS = [
        {
            "number": 1,
            "name": "Récupération",
            "hr": (50, 60),
            "vma": (55, 65),
        },
        {
            "number": 2,
            "name": "Endurance fondamentale",
            "hr": (60, 70),
            "vma": (65, 75),
        },
        {
            "number": 3,
            "name": "Endurance active",
            "hr": (70, 80),
            "vma": (75, 85),
        },
        {
            "number": 4,
            "name": "Seuil",
            "hr": (80, 90),
            "vma": (85, 95),
        },
        {
            "number": 5,
            "name": "VMA et intensité",
            "hr": (90, 100),
            "vma": (95, 105),
        },
    ]

    def calculate(
        self,
        maximum_heart_rate: int,
        vma_kmh: float,
    ) -> List[TrainingZone]:
        zones = []

        for definition in self.ZONE_DEFINITIONS:
            minimum_speed = round(
                vma_kmh
                * definition["vma"][0]
                / 100,
                1,
            )

            maximum_speed = round(
                vma_kmh
                * definition["vma"][1]
                / 100,
                1,
            )

            zone = TrainingZone(
                number=definition["number"],
                name=definition["name"],
                minimum_hr_percent=definition["hr"][0],
                maximum_hr_percent=definition["hr"][1],
                minimum_hr_bpm=round(
                    maximum_heart_rate
                    * definition["hr"][0]
                    / 100
                ),
                maximum_hr_bpm=round(
                    maximum_heart_rate
                    * definition["hr"][1]
                    / 100
                ),
                minimum_vma_percent=definition["vma"][0],
                maximum_vma_percent=definition["vma"][1],
                minimum_speed_kmh=minimum_speed,
                maximum_speed_kmh=maximum_speed,
                minimum_pace_seconds=speed_to_pace_seconds(
                    maximum_speed
                ),
                maximum_pace_seconds=speed_to_pace_seconds(
                    minimum_speed
                ),
            )

            zones.append(zone)

        return zones

    def display(
        self,
        zones: List[TrainingZone],
    ) -> None:
        print("=" * 60)
        print("ZONES D’ENTRAÎNEMENT ATLAS")
        print("=" * 60)

        for zone in zones:
            print()
            print(
                f"Z{zone.number} — {zone.name}"
            )

            print(
                f"FC : "
                f"{zone.minimum_hr_percent}–"
                f"{zone.maximum_hr_percent} % FCmax "
                f"({zone.minimum_hr_bpm}–"
                f"{zone.maximum_hr_bpm} bpm)"
            )

            print(
                f"VMA : "
                f"{zone.minimum_vma_percent}–"
                f"{zone.maximum_vma_percent} % "
                f"({zone.minimum_speed_kmh}–"
                f"{zone.maximum_speed_kmh} km/h)"
            )

            print(
                f"Allure : "
                f"{format_pace(zone.minimum_pace_seconds)} "
                f"à "
                f"{format_pace(zone.maximum_pace_seconds)}"
            )

        print()
        print(
            "SV1 estimé : transition Z2 → Z3"
        )
        print(
            "SV2 estimé : transition Z3 → Z4"
        )
        print("=" * 60)


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████