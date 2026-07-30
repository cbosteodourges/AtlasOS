"""
ATLAS OS
Prototype anatomique premium : cheville et pied droits.
"""

from src.anatomy.models import AnatomicalStructure, AnatomyRegistry


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — CONSTRUCTION DU MODÈLE
# ████████████████████████████████████████████████████████████

def build_right_ankle_foot() -> AnatomyRegistry:
    """
    Construit le premier registre anatomique de référence d'Atlas.

    Les valeurs mesh_id correspondent aux futurs noms des objets
    contenus dans le fichier GLB produit avec Blender.
    """

    registry = AnatomyRegistry(
        name="Complexe cheville–pied droit"
    )

    structures = [
        # --------------------------------------------------------
        # OS
        # --------------------------------------------------------
        AnatomicalStructure(
            structure_id="bone.tibia.right",
            name_fr="Tibia",
            structure_type="bone",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_bone_tibia_right",
            related_ids=[
                "bone.fibula.right",
                "bone.talus.right",
                "joint.talocrural.right",
            ],
            tags=["jambe", "cheville", "porteur"],
        ),
        AnatomicalStructure(
            structure_id="bone.fibula.right",
            name_fr="Fibula",
            structure_type="bone",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_bone_fibula_right",
            related_ids=[
                "bone.tibia.right",
                "bone.talus.right",
                "joint.talocrural.right",
            ],
            tags=["jambe", "malléole latérale"],
        ),
        AnatomicalStructure(
            structure_id="bone.talus.right",
            name_fr="Talus",
            structure_type="bone",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_bone_talus_right",
            related_ids=[
                "bone.tibia.right",
                "bone.fibula.right",
                "bone.calcaneus.right",
                "joint.talocrural.right",
                "joint.subtalar.right",
            ],
            tags=["cheville", "arrière-pied"],
        ),
        AnatomicalStructure(
            structure_id="bone.calcaneus.right",
            name_fr="Calcanéus",
            structure_type="bone",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_bone_calcaneus_right",
            related_ids=[
                "bone.talus.right",
                "joint.subtalar.right",
                "tendon.achilles.right",
                "fascia.plantar.right",
            ],
            tags=["talon", "arrière-pied"],
        ),

        # --------------------------------------------------------
        # ARTICULATIONS
        # --------------------------------------------------------
        AnatomicalStructure(
            structure_id="joint.talocrural.right",
            name_fr="Articulation talo-crurale",
            structure_type="joint",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_joint_talocrural_right",
            related_ids=[
                "bone.tibia.right",
                "bone.fibula.right",
                "bone.talus.right",
            ],
            tags=[
                "flexion dorsale",
                "flexion plantaire",
                "cheville",
            ],
        ),
        AnatomicalStructure(
            structure_id="joint.subtalar.right",
            name_fr="Articulation sous-talienne",
            structure_type="joint",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_joint_subtalar_right",
            related_ids=[
                "bone.talus.right",
                "bone.calcaneus.right",
            ],
            tags=[
                "inversion",
                "éversion",
                "arrière-pied",
            ],
        ),

        # --------------------------------------------------------
        # MUSCLES
        # --------------------------------------------------------
        AnatomicalStructure(
            structure_id="muscle.gastrocnemius.right",
            name_fr="Gastrocnémien",
            structure_type="muscle",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_muscle_gastrocnemius_right",
            related_ids=[
                "muscle.soleus.right",
                "tendon.achilles.right",
            ],
            tags=["mollet", "flexion plantaire"],
        ),
        AnatomicalStructure(
            structure_id="muscle.soleus.right",
            name_fr="Soléaire",
            structure_type="muscle",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_muscle_soleus_right",
            related_ids=[
                "muscle.gastrocnemius.right",
                "tendon.achilles.right",
            ],
            tags=["mollet profond", "flexion plantaire"],
        ),
        AnatomicalStructure(
            structure_id="muscle.tibialis_anterior.right",
            name_fr="Tibial antérieur",
            structure_type="muscle",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_muscle_tibialis_anterior_right",
            related_ids=[
                "joint.talocrural.right",
            ],
            tags=["flexion dorsale", "contrôle du pied"],
        ),

        # --------------------------------------------------------
        # TENDON
        # --------------------------------------------------------
        AnatomicalStructure(
            structure_id="tendon.achilles.right",
            name_fr="Tendon d’Achille",
            structure_type="tendon",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_tendon_achilles_right",
            related_ids=[
                "muscle.gastrocnemius.right",
                "muscle.soleus.right",
                "bone.calcaneus.right",
            ],
            tags=[
                "charge tendineuse",
                "course",
                "propulsion",
            ],
        ),

        # --------------------------------------------------------
        # FASCIA
        # --------------------------------------------------------
        AnatomicalStructure(
            structure_id="fascia.plantar.right",
            name_fr="Fascia plantaire",
            structure_type="fascia",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_fascia_plantar_right",
            related_ids=[
                "bone.calcaneus.right",
            ],
            tags=[
                "voûte plantaire",
                "aponévrose",
                "propulsion",
            ],
        ),

        # --------------------------------------------------------
        # NERF
        # --------------------------------------------------------
        AnatomicalStructure(
            structure_id="nerve.tibial.right",
            name_fr="Nerf tibial",
            structure_type="nerve",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_nerve_tibial_right",
            related_ids=[
                "bone.calcaneus.right",
                "fascia.plantar.right",
            ],
            tags=[
                "tunnel tarsien",
                "sensibilité plantaire",
            ],
        ),

        # --------------------------------------------------------
        # LIGAMENTS
        # --------------------------------------------------------
        AnatomicalStructure(
            structure_id="ligament.atfl.right",
            name_fr="Ligament talo-fibulaire antérieur",
            structure_type="ligament",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_ligament_atfl_right",
            related_ids=[
                "bone.fibula.right",
                "bone.talus.right",
                "joint.talocrural.right",
            ],
            tags=[
                "entorse latérale",
                "stabilité",
            ],
        ),
        AnatomicalStructure(
            structure_id="ligament.deltoid.right",
            name_fr="Ligament deltoïdien",
            structure_type="ligament",
            region="ankle_foot",
            side="right",
            mesh_id="mesh_ligament_deltoid_right",
            related_ids=[
                "bone.tibia.right",
                "bone.talus.right",
                "joint.talocrural.right",
            ],
            tags=[
                "stabilité médiale",
                "cheville",
            ],
        ),
    ]

    for structure in structures:
        registry.register(structure)

    return registry


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████