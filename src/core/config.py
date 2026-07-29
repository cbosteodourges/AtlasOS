"""
ATLAS OS
Configuration générale.
"""

from pathlib import Path


class Config:
    APP_NAME = "ATLAS OS"
    VERSION = "0.1.0"

    ROOT_DIR = Path(__file__).resolve().parents[2]

    DATA_DIR = ROOT_DIR / "atlas-data"
    ASSETS_DIR = ROOT_DIR / "assets"
    DOCS_DIR = ROOT_DIR / "docs"

    DEBUG = True

    @classmethod
    def afficher(cls):
        print("=" * 60)
        print("CONFIGURATION")
        print("=" * 60)
        print("Projet :", cls.APP_NAME)
        print("Version :", cls.VERSION)
        print("Racine :", cls.ROOT_DIR)
        print("Données :", cls.DATA_DIR)
        print("Assets :", cls.ASSETS_DIR)
        print("Documentation :", cls.DOCS_DIR)
        print("Debug :", cls.DEBUG)