"""
ATLAS OS
Moteur principal.
"""

from datetime import datetime

from src.anatomy import build_right_ankle_foot
from src.core.config import Config
from src.core.logger import AtlasLogger
from src.core.version import APP_NAME, VERSION
from src.patient.patient import Patient


class AtlasEngine:
    def __init__(self):
        self.start_time = datetime.now()

        self.patient = Patient(
            nom="Bonnet",
            prenom="Christophe",
            age=50,
            sexe="Homme",
            taille=1.86,
            poids=98,
            frequence_cardiaque=52,
            hrv=61,
            vo2max=51,
        )

        self.anatomy = build_right_ankle_foot()

    def start(self):
        AtlasLogger.info("Initialisation du moteur ATLAS")

        print("=" * 60)
        print(APP_NAME)
        print(f"Version : {VERSION}")
        print(f"Démarré : {self.start_time}")
        print("=" * 60)

        Config.afficher()
        AtlasLogger.info("Configuration chargée")

        print()
        self.patient.afficher()
        AtlasLogger.info("Patient chargé")

        print()
        self.anatomy.display_summary()
        AtlasLogger.info("Modèle anatomique chargé")

        AtlasLogger.info("ATLAS est opérationnel")