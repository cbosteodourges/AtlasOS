"""
ATLAS OS
Modèles de données du moteur anatomique.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — STRUCTURE ANATOMIQUE
# ████████████████████████████████████████████████████████████

@dataclass
class AnatomicalStructure:
    """
    Représente une structure anatomique reliée au futur modèle 3D.
    """

    structure_id: str
    name_fr: str
    structure_type: str
    region: str

    side: str = "central"
    mesh_id: Optional[str] = None

    parent_ids: List[str] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    visible_by_default: bool = True
    description: str = ""

    def display_name(self) -> str:
        if self.side == "right":
            return f"{self.name_fr} droit"
        if self.side == "left":
            return f"{self.name_fr} gauche"
        return self.name_fr


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — REGISTRE ANATOMIQUE
# ████████████████████████████████████████████████████████████

class AnatomyRegistry:
    """
    Registre central des structures anatomiques disponibles dans Atlas.
    """

    def __init__(self, name: str):
        self.name = name
        self._structures: Dict[str, AnatomicalStructure] = {}

    def register(self, structure: AnatomicalStructure) -> None:
        if structure.structure_id in self._structures:
            raise ValueError(
                f"La structure '{structure.structure_id}' existe déjà."
            )

        self._structures[structure.structure_id] = structure

    def get(self, structure_id: str) -> Optional[AnatomicalStructure]:
        return self._structures.get(structure_id)

    def all(self) -> List[AnatomicalStructure]:
        return list(self._structures.values())

    def by_type(self, structure_type: str) -> List[AnatomicalStructure]:
        return [
            structure
            for structure in self._structures.values()
            if structure.structure_type == structure_type
        ]

    def by_region(self, region: str) -> List[AnatomicalStructure]:
        return [
            structure
            for structure in self._structures.values()
            if structure.region == region
        ]

    def mesh_mapping(self) -> Dict[str, str]:
        """
        Produit la table reliant les objets Python aux pièces du modèle GLB.
        """

        return {
            structure.mesh_id: structure.structure_id
            for structure in self._structures.values()
            if structure.mesh_id
        }

    def count(self) -> int:
        return len(self._structures)

    def display_summary(self) -> None:
        print("=" * 60)
        print("ATLAS ANATOMY")
        print("=" * 60)
        print(f"Modèle : {self.name}")
        print(f"Structures enregistrées : {self.count()}")
        print()

        structure_types = sorted(
            {structure.structure_type for structure in self._structures.values()}
        )

        for structure_type in structure_types:
            structures = self.by_type(structure_type)

            print(
                f"{structure_type.capitalize()} : "
                f"{len(structures)}"
            )

            for structure in structures:
                print(
                    f"  - {structure.display_name()} "
                    f"[mesh: {structure.mesh_id or 'non défini'}]"
                )

        print("=" * 60)


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████