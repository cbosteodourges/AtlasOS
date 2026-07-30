"""
ATLAS OS
Analyse musculaire fonctionnelle.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — PROFIL MUSCULAIRE
# ████████████████████████████████████████████████████████████

@dataclass(frozen=True)
class MuscleProfile:
    identifier: str
    name: str
    functions: List[str] = field(default_factory=list)
    related_regions: List[str] = field(default_factory=list)
    assessment_suggestions: List[str] = field(default_factory=list)


@dataclass
class MuscleFinding:
    muscle_id: str
    muscle_name: str
    relevance_score: int
    functions: List[str]
    assessment_suggestions: List[str]


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — BASE MUSCULAIRE
# ████████████████████████████████████████████████████████████

def build_muscle_profiles() -> Dict[str, MuscleProfile]:
    profiles = [
        MuscleProfile(
            identifier="gastrocnemius",
            name="Gastrocnémien",
            functions=[
                "Flexion plantaire",
                "Participation à la flexion du genou",
                "Propulsion",
            ],
            related_regions=[
                "calf",
                "ankle",
                "achilles",
                "knee",
            ],
            assessment_suggestions=[
                "Élévation unipodale sur la pointe du pied",
                "Souplesse genou tendu",
                "Symétrie de force et d'endurance",
            ],
        ),
        MuscleProfile(
            identifier="soleus",
            name="Soléaire",
            functions=[
                "Flexion plantaire",
                "Contrôle antérieur du tibia",
                "Stabilisation en charge",
            ],
            related_regions=[
                "calf",
                "ankle",
                "achilles",
            ],
            assessment_suggestions=[
                "Élévation du talon genou fléchi",
                "Souplesse genou fléchi",
                "Endurance du triceps sural",
            ],
        ),
        MuscleProfile(
            identifier="gluteus_medius",
            name="Moyen fessier",
            functions=[
                "Abduction de hanche",
                "Stabilisation du bassin",
                "Contrôle du membre inférieur",
            ],
            related_regions=[
                "hip",
                "pelvis",
                "knee",
                "ankle",
                "running",
            ],
            assessment_suggestions=[
                "Appui unipodal",
                "Step-down",
                "Contrôle du bassin à la course",
            ],
        ),
        MuscleProfile(
            identifier="tibialis_posterior",
            name="Tibial postérieur",
            functions=[
                "Soutien de l'arche médiale",
                "Inversion",
                "Contrôle de la pronation",
            ],
            related_regions=[
                "medial_ankle",
                "foot",
                "arch",
                "running",
            ],
            assessment_suggestions=[
                "Élévation unipodale du talon",
                "Contrôle de l'arche médiale",
                "Force en inversion",
            ],
        ),
        MuscleProfile(
            identifier="quadriceps",
            name="Quadriceps",
            functions=[
                "Extension du genou",
                "Absorption des contraintes",
                "Contrôle de la flexion en charge",
            ],
            related_regions=[
                "knee",
                "patella",
                "squat",
                "running",
            ],
            assessment_suggestions=[
                "Squat",
                "Step-down",
                "Force isométrique ou dynamique",
            ],
        ),
    ]

    return {
        profile.identifier: profile
        for profile in profiles
    }


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟨 PARTIE C — ANALYSEUR MUSCULAIRE
# ████████████████████████████████████████████████████████████

class MuscleAnalyzer:
    def __init__(self) -> None:
        self.profiles = build_muscle_profiles()

    def analyse(
        self,
        structure_id: str,
        context: str = "",
    ) -> List[MuscleFinding]:
        normalized = self._normalize(
            f"{structure_id}_{context}"
        )

        findings: List[MuscleFinding] = []

        for profile in self.profiles.values():
            score = 0

            if profile.identifier in normalized:
                score += 90

            for region in profile.related_regions:
                if region in normalized:
                    score += 20

            if (
                "achilles" in normalized
                and profile.identifier
                in {"gastrocnemius", "soleus"}
            ):
                score += 70

            if (
                "running" in normalized
                and profile.identifier
                in {
                    "gluteus_medius",
                    "gastrocnemius",
                    "soleus",
                }
            ):
                score += 15

            if score > 0:
                findings.append(
                    MuscleFinding(
                        muscle_id=profile.identifier,
                        muscle_name=profile.name,
                        relevance_score=min(100, score),
                        functions=profile.functions,
                        assessment_suggestions=(
                            profile.assessment_suggestions
                        ),
                    )
                )

        return sorted(
            findings,
            key=lambda finding: finding.relevance_score,
            reverse=True,
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