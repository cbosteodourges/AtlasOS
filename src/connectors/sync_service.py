"""
ATLAS OS
Service commun de synchronisation des activités.
"""

from typing import List, Optional

from .activity_schema import NormalizedActivity
from .registry import ConnectorRegistry


class ActivitySyncService:
    """Pilote la connexion, l'importation et la normalisation."""

    def __init__(self, registry: ConnectorRegistry) -> None:
        self.registry = registry

    def synchronize(
        self,
        provider: str,
        since: Optional[str] = None,
    ) -> List[NormalizedActivity]:
        """Synchronise les activités d'un fournisseur."""
        connector = self.registry.get(provider)
        connector.connect()

        normalized_activities: List[NormalizedActivity] = []

        for activity in connector.fetch_activities(since=since):
            normalized_activities.append(
                connector.normalize(activity)
            )

        return normalized_activities