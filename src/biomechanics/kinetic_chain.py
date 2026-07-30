"""
ATLAS OS
Analyse des chaînes cinétiques.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — CHAÎNE CINÉTIQUE
# ████████████████████████████████████████████████████████████

@dataclass(frozen=True)
class KineticChain:
    identifier: str
    name: str
    structures: List[str] = field(default_factory=list)
    possible_consequences: List[str] = field(default_factory=list)


@dataclass
class KineticChainFinding:
    chain_id: str
    chain_name: str
    involved_structures: List[str]
    possible_consequences: List[str]
    relevance_score: int


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — RÉFÉRENTIEL
# ████████████████████████████████████████████████████████████

def build_default_kinetic_chains() -> Dict[str, KineticChain]:
    chains = [
        KineticChain(
            identifier="posterior_lower_limb",
            name="Chaîne postérieure du membre inférieur",
            structures=[
                "lumbar_spine",
                "pelvis",
                "gluteus_maximus",
                "hamstrings",
                "gastrocnemius",
                "soleus",
                "achilles_tendon",
                "plantar_fascia",
            ],
            possible_consequences=[
                "Réduction de la propulsion",
                "Augmentation des contraintes postérieures",
                "Altération de la longueur de pas",
            ],
        ),
        KineticChain(
            identifier="lateral_stability",
            name="Chaîne latérale de stabilité",
            structures=[
                "lumbo_pelvic",
                "gluteus_medius",
                "gluteus_minimus",
                "iliotibial_band",
                "lateral_knee",
                "fibularis",
                "lateral_ankle",
            ],
            possible_consequences=[
                "Instabilité pelvienne",
                "Valgus dynamique",
                "Surcharge latérale du genou ou de la cheville",
            ],
        ),
        KineticChain(
            identifier="medial_lower_limb",
            name="Chaîne médiale du membre inférieur",
            structures=[
                "adductors",
                "medial_knee",
                "tibialis_posterior",
                "medial_ankle",
                "medial_arch",
            ],
            possible_consequences=[
                "Affaissement de l'arche médiale",
                "Rotation interne du membre inférieur",
                "Augmentation des contraintes médiales",
            ],
        ),
        KineticChain(
            identifier="upper_quarter",
            name="Chaîne cervico-scapulo-brachiale",
            structures=[
                "cervical_spine",
                "thoracic_spine",
                "scapula",
                "rotator_cuff",
                "shoulder",
                "elbow",
                "wrist",
            ],
            possible_consequences=[
                "Altération du rythme scapulo-huméral",
                "Surcharge de l'épaule",
                "Compensation cervicale",
            ],
        ),
    ]

    return {
        chain.identifier: chain
        for chain in chains
    }


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟨 PARTIE C — ANALYSEUR
# ████████████████████████████████████████████████████████████

class KineticChainAnalyzer:
    def __init__(self) -> None:
        self.chains = build_default_kinetic_chains()

    def analyse(
        self,
        structure_id: str,
    ) -> List[KineticChainFinding]:
        normalized = self._normalize(structure_id)
        findings: List[KineticChainFinding] = []

        keywords = set(
            normalized.replace(".", "_").split("_")
        )

        for chain in self.chains.values():
            relevance = 0
            involved: List[str] = []

            for structure in chain.structures:
                structure_normalized = self._normalize(structure)
                structure_keywords = set(
                    structure_normalized.split("_")
                )

                if structure_normalized in normalized:
                    relevance += 45
                    involved.append(structure)
                elif keywords.intersection(structure_keywords):
                    relevance += 12
                    involved.append(structure)

            if relevance > 0:
                findings.append(
                    KineticChainFinding(
                        chain_id=chain.identifier,
                        chain_name=chain.name,
                        involved_structures=list(
                            dict.fromkeys(involved)
                        ),
                        possible_consequences=(
                            chain.possible_consequences
                        ),
                        relevance_score=min(100, relevance),
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
            .replace("-", "_")
            .replace(" ", "_")
            .replace("tendon.achilles", "achilles_tendon")
            .replace("achilles", "achilles_tendon")
        )


# ████████████████████████████████████████████████████████████
# 🟨 FIN PARTIE C
# ████████████████████████████████████████████████████████████