"""
ATLAS OS
Point d'entrée principal
"""

from src.core.atlas_engine import AtlasEngine


def main():

    engine = AtlasEngine()

    engine.start()


if __name__ == "__main__":
    main()