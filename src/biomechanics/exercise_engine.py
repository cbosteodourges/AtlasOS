"""
ATLAS OS
Génération prudente d'exercices biomécaniques.
"""

from dataclasses import dataclass, field
from typing import List


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — EXERCICE
# ████████████████████████████████████████████████████████████

@dataclass
class BiomechanicalExercise:
    identifier: str
    name: str
    category: str
    instructions: str
    dosage: str
    objective: str
    precautions: List[str] = field(default_factory=list)


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — GÉNÉRATEUR
# ████████████████████████████████████████████████████████████

class ExerciseEngine:
    def generate(
        self,
        structure_id: str,
        pain_intensity: int,
        risk_score: int,
    ) -> List[BiomechanicalExercise]:
        normalized = self._normalize(structure_id)

        if pain_intensity >= 7 or risk_score >= 75:
            return [
                BiomechanicalExercise(
                    identifier="relative_rest",
                    name="Mise au repos relatif",
                    category="protection",
                    instructions=(
                        "Suspendre les exercices provoquant "
                        "nettement les symptômes et conserver "
                        "uniquement les activités confortables."
                    ),
                    dosage="À adapter selon les symptômes",
                    objective=(
                        "Éviter une aggravation avant réévaluation."
                    ),
                    precautions=[
                        "Demander un avis professionnel rapidement.",
                        "Ne pas forcer dans la douleur importante.",
                    ],
                )
            ]

        if "achilles" in normalized:
            return self._achilles_program(
                pain_intensity
            )

        if "knee" in normalized:
            return self._knee_program()

        if "hip" in normalized:
            return self._hip_program()

        return self._generic_program()

    def _achilles_program(
        self,
        pain_intensity: int,
    ) -> List[BiomechanicalExercise]:
        dosage = (
            "5 répétitions de 30 à 45 secondes"
            if pain_intensity >= 4
            else "3 séries de 12 répétitions"
        )

        return [
            BiomechanicalExercise(
                identifier="calf_isometric",
                name="Contraction isométrique du mollet",
                category="force",
                instructions=(
                    "Monter légèrement sur la pointe des pieds "
                    "et maintenir la position sans augmenter "
                    "nettement la douleur."
                ),
                dosage=dosage,
                objective=(
                    "Réintroduire progressivement la charge "
                    "sur le complexe suro-achilléen."
                ),
                precautions=[
                    "Rester dans une douleur tolérable.",
                    "Contrôler la réponse le lendemain.",
                ],
            ),
            BiomechanicalExercise(
                identifier="ankle_mobility",
                name="Mobilité contrôlée de cheville",
                category="mobilité",
                instructions=(
                    "Avancer doucement le genou au-dessus du pied "
                    "en gardant le talon au sol."
                ),
                dosage="2 séries de 10 mouvements lents",
                objective=(
                    "Entretenir la dorsiflexion de cheville."
                ),
                precautions=[
                    "Ne pas provoquer de douleur vive.",
                ],
            ),
            BiomechanicalExercise(
                identifier="single_leg_balance",
                name="Équilibre unipodal",
                category="contrôle moteur",
                instructions=(
                    "Maintenir l'appui sur une jambe avec "
                    "le bassin horizontal et le pied stable."
                ),
                dosage="3 fois 30 secondes",
                objective=(
                    "Améliorer le contrôle du membre inférieur."
                ),
                precautions=[
                    "Se placer près d'un support stable.",
                ],
            ),
        ]

    @staticmethod
    def _knee_program() -> List[BiomechanicalExercise]:
        return [
            BiomechanicalExercise(
                identifier="wall_sit",
                name="Chaise contre un mur",
                category="force",
                instructions=(
                    "Maintenir une flexion confortable des genoux "
                    "avec le dos appuyé contre un mur."
                ),
                dosage="4 fois 30 secondes",
                objective=(
                    "Renforcer progressivement le quadriceps."
                ),
                precautions=[
                    "Réduire l'angle en cas d'inconfort.",
                ],
            )
        ]

    @staticmethod
    def _hip_program() -> List[BiomechanicalExercise]:
        return [
            BiomechanicalExercise(
                identifier="hip_abduction",
                name="Abduction de hanche contrôlée",
                category="force",
                instructions=(
                    "Éloigner lentement la jambe sur le côté "
                    "sans incliner le bassin."
                ),
                dosage="3 séries de 12 répétitions",
                objective=(
                    "Renforcer les stabilisateurs latéraux "
                    "de la hanche."
                ),
                precautions=[
                    "Éviter les compensations du tronc.",
                ],
            )
        ]

    @staticmethod
    def _generic_program() -> List[BiomechanicalExercise]:
        return [
            BiomechanicalExercise(
                identifier="comfortable_mobility",
                name="Mobilité active confortable",
                category="mobilité",
                instructions=(
                    "Mobiliser lentement la région concernée "
                    "dans une amplitude confortable."
                ),
                dosage="2 séries de 10 répétitions",
                objective=(
                    "Maintenir la mobilité sans surcharge."
                ),
                precautions=[
                    "Arrêter en cas de douleur vive ou inhabituelle.",
                ],
            )
        ]

    @staticmethod
    def _normalize(value: str) -> str:
        return (
            value.lower()
            .replace(".", "_")
            .replace("-", "_")
            .replace(" ", "_")
        )


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████