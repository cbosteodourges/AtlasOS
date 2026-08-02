"""
ATLAS OS
Registre central des connecteurs de données.
"""

from typing import Dict, List

from .base import ActivityConnector


class ConnectorRegistry:
    """Stocke et retrouve les connecteurs par fournisseur."""

    def __init__(self) -> None:
        self._connectors: Dict[str, ActivityConnector] = {}

    def register(
        self,
        connector: ActivityConnector,
        replace: bool = False,
    ) -> None:
        """Ajoute un connecteur au registre."""
        provider = connector.provider.strip().lower()

        if not provider:
            raise ValueError(
                "Le fournisseur du connecteur ne peut pas être vide."
            )

        if provider in self._connectors and not replace:
            raise ValueError(
                f"Le connecteur '{provider}' est déjà enregistré."
            )

        self._connectors[provider] = connector

    def get(self, provider: str) -> ActivityConnector:
        """Retourne le connecteur correspondant au fournisseur."""
        normalized_provider = provider.strip().lower()

        try:
            return self._connectors[normalized_provider]
        except KeyError as error:
            raise KeyError(
                f"Aucun connecteur enregistré pour '{provider}'."
            ) from error

    def contains(self, provider: str) -> bool:
        """Indique si un fournisseur est enregistré."""
        return provider.strip().lower() in self._connectors

    def providers(self) -> List[str]:
        """Retourne la liste triée des fournisseurs disponibles."""
        return sorted(self._connectors)

    def unregister(self, provider: str) -> None:
        """Retire un connecteur du registre."""
        normalized_provider = provider.strip().lower()

        if normalized_provider not in self._connectors:
            raise KeyError(
                f"Aucun connecteur enregistré pour '{provider}'."
            )

        del self._connectors[normalized_provider]