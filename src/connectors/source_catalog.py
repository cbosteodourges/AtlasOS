"""Catalogue des sources de données supportées par ATLAS OS.

Ce module décrit les capacités réelles sans présenter une intégration fournisseur
comme opérationnelle avant obtention des autorisations et identifiants nécessaires.
"""

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class SourceCapability:
    provider: str
    label: str
    activity_transport: str
    activity_formats: Tuple[str, ...]
    wellness_supported: bool
    incremental_supported: bool
    connection_status: str
    requires_vendor_authorization: bool
    notes: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["activity_formats"] = list(self.activity_formats)
        return payload


_SOURCE_CATALOG: Dict[str, SourceCapability] = {
    "garmin": SourceCapability(
        "garmin", "Garmin", "local_fit", ("fit",), True, True,
        "operational", False,
        "Import FIT local et données Wellness déjà opérationnels.",
    ),
    "strava": SourceCapability(
        "strava", "Strava", "oauth_api", ("json",), False, True,
        "backend_ready", True,
        "Connecteur API prêt ; l'activation exige une application Strava et OAuth.",
    ),
    "health_connect": SourceCapability(
        "health_connect", "Health Connect", "mobile_bridge", ("json",), True, True,
        "bridge_required", True,
        "Une application Android doit transmettre les données autorisées à Atlas.",
    ),
    "polar": SourceCapability(
        "polar", "Polar Flow", "vendor_api_or_export", ("fit", "tcx", "csv"), True, True,
        "authorization_required", True,
        "Nécessite Polar AccessLink ou un export utilisateur normalisé.",
    ),
    "suunto": SourceCapability(
        "suunto", "Suunto", "vendor_api_or_export", ("fit",), False, True,
        "authorization_required", True,
        "Nécessite l'accès partenaire Suunto ou un export FIT.",
    ),
    "coros": SourceCapability(
        "coros", "COROS", "vendor_api_or_export", ("fit", "tcx"), False, True,
        "authorization_required", True,
        "Nécessite l'API COROS ou un export utilisateur.",
    ),
    "manual": SourceCapability(
        "manual", "Sans montre connectée", "manual_entry", (), True, True,
        "operational", False,
        "Ressenti, récupération, douleur et séances peuvent être saisis manuellement.",
    ),
}

_ALIASES = {
    "health connect": "health_connect",
    "health-connect": "health_connect",
    "google health connect": "health_connect",
    "polar flow": "polar",
    "sans montre": "manual",
    "no watch": "manual",
}


def canonical_provider(provider: str) -> str:
    key = provider.strip().lower().replace("é", "e")
    return _ALIASES.get(key, key.replace(" ", "_"))


def get_source_capability(provider: str) -> SourceCapability:
    canonical = canonical_provider(provider)
    if canonical not in _SOURCE_CATALOG:
        raise KeyError(f"Source Atlas inconnue : {provider}")
    return _SOURCE_CATALOG[canonical]


def list_source_capabilities() -> Tuple[SourceCapability, ...]:
    order = ("health_connect", "garmin", "polar", "suunto", "coros", "strava", "manual")
    return tuple(_SOURCE_CATALOG[key] for key in order)
