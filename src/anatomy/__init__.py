"""
ATLAS OS
Module anatomique.
"""

from src.anatomy.ankle_foot import build_right_ankle_foot
from src.anatomy.models import AnatomicalStructure, AnatomyRegistry

__all__ = [
    "AnatomicalStructure",
    "AnatomyRegistry",
    "build_right_ankle_foot",
]