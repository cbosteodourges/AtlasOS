"""
ATLAS OS
Référentiel des mouvements biomécaniques.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — MODÈLE DE MOUVEMENT
# ████████████████████████████████████████████████████████████

@dataclass(frozen=True)
class MovementPattern:
    identifier: str
    name: str
    description: str
    primary_joints: List[str] = field(default_factory=list)
    primary_muscles: List[str] = field(default_factory=list)
    common_compensations: List[str] = field(default_factory=list)


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — BIBLIOTHÈQUE DES MOUVEMENTS
# ████████████████████████████████████████████████████████████

def build_default_movement_patterns() -> Dict[str, MovementPattern]:
    patterns = [
        MovementPattern(
            identifier="walking",
            name="Marche",
            description=(
                "Déplacement cyclique alternant appui, propulsion "
                "et phase oscillante."
            ),
            primary_joints=[
                "hip",
                "knee",
                "ankle",
                "foot",
            ],
            primary_muscles=[
                "gluteus_maximus",
                "gluteus_medius",
                "quadriceps",
                "hamstrings",
                "gastrocnemius",
                "soleus",
                "tibialis_anterior",
            ],
            common_compensations=[
                "Réduction de la propulsion",
                "Rotation excessive du bassin",
                "Affaissement médial du genou",
            ],
        ),
        MovementPattern(
            identifier="running",
            name="Course à pied",
            description=(
                "Locomotion avec phases d'appui unipodal, "
                "de propulsion et de suspension."
            ),
            primary_joints=[
                "lumbo_pelvic",
                "hip",
                "knee",
                "ankle",
                "foot",
            ],
            primary_muscles=[
                "gluteus_maximus",
                "gluteus_medius",
                "quadriceps",
                "hamstrings",
                "gastrocnemius",
                "soleus",
                "tibialis_posterior",
                "fibularis",
            ],
            common_compensations=[
                "Sur-stride",
                "Cadence insuffisante",
                "Adduction excessive de hanche",
                "Pronation prolongée",
                "Rigidité de cheville",
            ],
        ),
        MovementPattern(
            identifier="squat",
            name="Squat",
            description=(
                "Flexion coordonnée des hanches, genoux "
                "et chevilles avec contrôle du tronc."
            ),
            primary_joints=[
                "lumbar_spine",
                "hip",
                "knee",
                "ankle",
            ],
            primary_muscles=[
                "erector_spinae",
                "gluteus_maximus",
                "quadriceps",
                "hamstrings",
                "soleus",
            ],
            common_compensations=[
                "Valgus dynamique",
                "Décollement des talons",
                "Flexion excessive du tronc",
                "Asymétrie d'appui",
            ],
        ),
        MovementPattern(
            identifier="single_leg_support",
            name="Appui unipodal",
            description=(
                "Maintien du centre de masse au-dessus "
                "d'un seul membre inférieur."
            ),
            primary_joints=[
                "sacroiliac",
                "hip",
                "knee",
                "ankle",
                "foot",
            ],
            primary_muscles=[
                "gluteus_medius",
                "gluteus_minimus",
                "quadriceps",
                "tibialis_posterior",
                "fibularis",
                "intrinsic_foot",
            ],
            common_compensations=[
                "Chute controlatérale du bassin",
                "Valgus du genou",
                "Instabilité de cheville",
                "Agrippement des orteils",
            ],
        ),
        MovementPattern(
            identifier="push",
            name="Poussée du membre supérieur",
            description=(
                "Mouvement associant stabilisation scapulaire, "
                "flexion ou adduction d'épaule et extension du coude."
            ),
            primary_joints=[
                "thoracic_spine",
                "scapulothoracic",
                "shoulder",
                "elbow",
                "wrist",
            ],
            primary_muscles=[
                "serratus_anterior",
                "pectoralis_major",
                "deltoid",
                "triceps",
            ],
            common_compensations=[
                "Élévation de l'épaule",
                "Décollement de la scapula",
                "Hyperextension lombaire",
            ],
        ),
    ]

    return {
        pattern.identifier: pattern
        for pattern in patterns
    }


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████