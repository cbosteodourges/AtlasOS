"""
ATLAS Engine
"""

from datetime import datetime

from src.core.version import APP_NAME, VERSION
from src.core.config import Config
from src.core.logger import AtlasLogger


class AtlasEngine:

    def __init__(self):
        self.start_time = datetime.now()

    def start(self):

        AtlasLogger.info("Initialisation du moteur ATLAS")

        print("=" * 60)
        print(APP_NAME)
        print(f"Version : {VERSION}")
        print(f"Démarré : {self.start_time}")
        print("=" * 60)

        Config.afficher()

        AtlasLogger.info("Configuration chargée")

        AtlasLogger.info("ATLAS est opérationnel")