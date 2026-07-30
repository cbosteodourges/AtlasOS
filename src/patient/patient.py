"""
ATLAS OS
Module Patient
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Patient:

    # ------------------------
    # Identité
    # ------------------------
    nom: str = ""
    prenom: str = ""
    age: int = 0
    sexe: str = ""

    # ------------------------
    # Morphologie
    # ------------------------
    taille: float = 0.0
    poids: float = 0.0

    # ------------------------
    # Physiologie
    # ------------------------
    frequence_cardiaque: int = 0
    hrv: int = 0
    vo2max: float = 0.0

    # ------------------------
    # Biomécanique
    # ------------------------
    douleurs: List[str] = field(default_factory=list)
    articulations: List[str] = field(default_factory=list)
    muscles: List[str] = field(default_factory=list)

    # ------------------------
    # Clinique
    # ------------------------
    traitements: List[str] = field(default_factory=list)
    antecedents: List[str] = field(default_factory=list)

    @property
    def imc(self):

        if self.taille == 0:
            return 0

        return round(self.poids / (self.taille ** 2), 2)

    def afficher(self):

        print("=" * 60)
        print("PATIENT")
        print("=" * 60)

        print(f"Nom : {self.nom}")
        print(f"Prénom : {self.prenom}")
        print(f"Age : {self.age}")
        print(f"Sexe : {self.sexe}")

        print()

        print(f"Taille : {self.taille} m")
        print(f"Poids : {self.poids} kg")
        print(f"IMC : {self.imc}")

        print()

        print(f"FC : {self.frequence_cardiaque}")
        print(f"HRV : {self.hrv}")
        print(f"VO2max : {self.vo2max}")

        print("=" * 60)