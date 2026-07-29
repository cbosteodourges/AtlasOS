"""
ATLAS OS
Moteur principal du Digital Twin
"""

from datetime import datetime


class AtlasEngine:

    def __init__(self):
        self.version = "0.1.0"
        self.started_at = datetime.now()

    def start(self):
        print("=" * 60)
        print("ATLAS ENGINE")
        print(f"Version : {self.version}")
        print(f"Démarré : {self.started_at}")
        print("=" * 60)