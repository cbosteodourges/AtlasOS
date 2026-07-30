"""
ATLAS OS
Cartographie biomécanique des douleurs.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — CARTOGRAPHIE
# ████████████████████████████████████████████████████████████

@dataclass(frozen=True)
class PainMap:
    key: str
    display_name: str
    related_structures: List[str] = field(default_factory=list)
    possible_mechanisms: List[str] = field(default_factory=list)
    assessment_axes: List[str] = field(default_factory=list)


@dataclass
class PainMappingResult:
    source_structure_id: str
    display_name: str
    related_structures: List[str]
    possible_mechanisms: List[str]
    assessment_axes: List[str]
    confidence_score: int


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — BASE DE CARTOGRAPHIE
# ████████████████████████████████████████████████████████████

def build_pain_maps() -> Dict[str, PainMap]:
    maps = [
        PainMap(
            key="achilles",
            display_name="Région du tendon d'Achille",
            related_structures=[
                "Tendon d'Achille",
                "Gastrocnémien",
                "Soléaire",
                "Calcanéus",
                "Articulation talo-crurale",
                "Fascia plantaire",
                "Moyen fessier",
            ],
            possible_mechanisms=[
                "Augmentation récente de la charge",
                "Tolérance insuffisante du complexe suro-achilléen",
                "Déficit de force ou d'endurance du mollet",
                "Dorsiflexion de cheville insuffisante",
                "Modification de terrain, chaussures ou technique",
            ],
            assessment_axes=[
                "Localisation exacte de la douleur",
                "Réponse à la mise en charge",
                "Raideur matinale",
                "Force et endurance du mollet",
                "Mobilité de cheville",
                "Évolution à 24 heures après l'effort",
            ],
        ),
        PainMap(
            key="knee",
            display_name="Région du genou",
            related_structures=[
                "Articulation fémoro-patellaire",
                "Tendon patellaire",
                "Quadriceps",
                "Ménisques",
                "Hanche",
                "Cheville",
            ],
            possible_mechanisms=[
                "Surcharge progressive",
                "Déficit de contrôle du membre inférieur",
                "Tolérance insuffisante du quadriceps",
                "Variation rapide du volume ou du dénivelé",
            ],
            assessment_axes=[
                "Zone douloureuse précise",
                "Douleur à l'escalier",
                "Contrôle lors du squat",
                "Mobilité de hanche et de cheville",
            ],
        ),
        PainMap(
            key="hip",
            display_name="Région de la hanche",
            related_structures=[
                "Moyen fessier",
                "Grand fessier",
                "Tendons fessiers",
                "Articulation coxo-fémorale",
                "Région lombo-pelvienne",
            ],
            possible_mechanisms=[
                "Déficit de tolérance des abducteurs",
                "Compression latérale prolongée",
                "Surcharge en appui unipodal",
                "Déficit de contrôle lombo-pelvien",
            ],
            assessment_axes=[
                "Douleur latérale, antérieure ou postérieure",
                "Réponse à l'appui unipodal",
                "Force des abducteurs",
                "Mobilité de hanche",
            ],
        ),
        PainMap(
            key="shoulder",
            display_name="Région de l'épaule",
            related_structures=[
                "Coiffe des rotateurs",
                "Deltoïde",
                "Scapula",
                "Rachis thoracique",
                "Articulation acromio-claviculaire",
            ],
            possible_mechanisms=[
                "Tolérance réduite à l'élévation",
                "Déficit de contrôle scapulaire",
                "Variation rapide de charge",
                "Limitation thoracique ou gléno-humérale",
            ],
            assessment_axes=[
                "Arc douloureux",
                "Force en rotation",
                "Mobilité thoracique",
                "Contrôle scapulaire",
            ],
        ),
    ]

    return {
        pain_map.key: pain_map
        for pain_map in maps
    }


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟨 PARTIE C — MOTEUR DE CARTOGRAPHIE
# ████████████████████████████████████████████████████████████

class PainMapper:
    def __init__(self) -> None:
        self.maps = build_pain_maps()

    def map_pain(
        self,
        structure_id: str,
    ) -> PainMappingResult:
        normalized = self._normalize(structure_id)

        selected: PainMap | None = None
        confidence = 35

        for key, pain_map in self.maps.items():
            if key in normalized:
                selected = pain_map
                confidence = 90
                break

        if selected is None:
            selected = PainMap(
                key="generic",
                display_name=structure_id.replace(
                    ".", " "
                ).replace("_", " ").title(),
                related_structures=[
                    "Articulations adjacentes",
                    "Muscles locaux",
                    "Structures de la chaîne cinétique",
                ],
                possible_mechanisms=[
                    "Surcharge locale",
                    "Variation récente d'activité",
                    "Déficit de tolérance tissulaire",
                ],
                assessment_axes=[
                    "Localisation précise",
                    "Intensité",
                    "Facteurs aggravants et soulageants",
                    "Évolution temporelle",
                ],
            )

        return PainMappingResult(
            source_structure_id=structure_id,
            display_name=selected.display_name,
            related_structures=selected.related_structures,
            possible_mechanisms=selected.possible_mechanisms,
            assessment_axes=selected.assessment_axes,
            confidence_score=confidence,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return (
            value.lower()
            .replace(".", "_")
            .replace("-", "_")
            .replace(" ", "_")
        )


# ████████████████████████████████████████████████████████████
# 🟨 FIN PARTIE C
# ████████████████████████████████████████████████████████████