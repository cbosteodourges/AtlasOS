"""
ATLAS OS
Analyse biomécanique articulaire.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — MODÈLES ARTICULAIRES
# ████████████████████████████████████████████████████████████

@dataclass(frozen=True)
class JointProfile:
    identifier: str
    name: str
    movements: List[str] = field(default_factory=list)
    associated_structures: List[str] = field(default_factory=list)
    common_limitations: List[str] = field(default_factory=list)


@dataclass
class JointFinding:
    joint_id: str
    joint_name: str
    relevance_score: int
    movements_to_assess: List[str]
    possible_limitations: List[str]


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — BASE ARTICULAIRE
# ████████████████████████████████████████████████████████████

def build_joint_profiles() -> Dict[str, JointProfile]:
    profiles = [
        JointProfile(
            identifier="ankle",
            name="Cheville",
            movements=[
                "Dorsiflexion",
                "Flexion plantaire",
                "Inversion",
                "Éversion",
            ],
            associated_structures=[
                "achilles_tendon",
                "gastrocnemius",
                "soleus",
                "tibialis_anterior",
                "tibialis_posterior",
                "fibularis",
                "talus",
                "calcaneus",
            ],
            common_limitations=[
                "Dorsiflexion limitée",
                "Instabilité latérale",
                "Contrôle insuffisant de la pronation",
            ],
        ),
        JointProfile(
            identifier="knee",
            name="Genou",
            movements=[
                "Flexion",
                "Extension",
                "Rotation en flexion",
            ],
            associated_structures=[
                "quadriceps",
                "hamstrings",
                "patellar_tendon",
                "iliotibial_band",
                "meniscus",
            ],
            common_limitations=[
                "Valgus dynamique",
                "Déficit d'extension",
                "Contrôle excentrique insuffisant",
            ],
        ),
        JointProfile(
            identifier="hip",
            name="Hanche",
            movements=[
                "Flexion",
                "Extension",
                "Abduction",
                "Adduction",
                "Rotations",
            ],
            associated_structures=[
                "gluteus_maximus",
                "gluteus_medius",
                "gluteus_minimus",
                "iliopsoas",
                "adductors",
                "hamstrings",
            ],
            common_limitations=[
                "Extension limitée",
                "Faiblesse des abducteurs",
                "Rotation interne excessive en charge",
            ],
        ),
        JointProfile(
            identifier="shoulder",
            name="Épaule",
            movements=[
                "Flexion",
                "Extension",
                "Abduction",
                "Adduction",
                "Rotations",
            ],
            associated_structures=[
                "rotator_cuff",
                "deltoid",
                "scapula",
                "pectoralis_major",
                "latissimus_dorsi",
            ],
            common_limitations=[
                "Déficit de rotation",
                "Altération du contrôle scapulaire",
                "Élévation compensatrice",
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
# 🟨 PARTIE C — ANALYSEUR ARTICULAIRE
# ████████████████████████████████████████████████████████████

class JointAnalyzer:
    def __init__(self) -> None:
        self.profiles = build_joint_profiles()

    def analyse(
        self,
        structure_id: str,
    ) -> List[JointFinding]:
        normalized = self._normalize(structure_id)
        findings: List[JointFinding] = []

        for profile in self.profiles.values():
            score = 0

            if profile.identifier in normalized:
                score += 70

            for associated_structure in (
                profile.associated_structures
            ):
                if associated_structure in normalized:
                    score += 55

            if (
                "achilles" in normalized
                and profile.identifier == "ankle"
            ):
                score += 80

            if score > 0:
                findings.append(
                    JointFinding(
                        joint_id=profile.identifier,
                        joint_name=profile.name,
                        relevance_score=min(100, score),
                        movements_to_assess=profile.movements,
                        possible_limitations=(
                            profile.common_limitations
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