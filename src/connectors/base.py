"""
ATLAS OS
Contrat commun des connecteurs d'activités.
"""

from abc import ABC, abstractmethod
from typing import Iterable

from .activity_schema import ActivitySample, NormalizedActivity


class ActivityConnector(ABC):
    """Base commune à tous les fournisseurs."""

    provider: str

    @abstractmethod
    def connect(self) -> None:
        """Initialise la connexion au fournisseur."""
        raise NotImplementedError

    @abstractmethod
    def fetch_activities(
        self,
        since: str | None = None,
    ) -> Iterable[ActivitySample]:
        """Récupère les activités nouvelles ou modifiées."""
        raise NotImplementedError

    @abstractmethod
    def normalize(
        self,
        activity: ActivitySample,
    ) -> NormalizedActivity:
        """Convertit une activité au format commun ATLAS."""
        raise NotImplementedError