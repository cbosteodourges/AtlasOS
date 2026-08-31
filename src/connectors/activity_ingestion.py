"""Stockage idempotent et fusion multi-source des activités Atlas."""

from dataclasses import fields
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .activity_schema import ActivitySample, NormalizedActivity


def activity_fingerprint(activity: NormalizedActivity) -> str:
    start = datetime.fromisoformat(activity.start_time.replace("Z", "+00:00"))
    start = start.astimezone(timezone.utc).replace(second=0, microsecond=0)
    signature = "|".join((
        activity.activity_type.lower(), start.isoformat(),
        str(round(activity.duration_seconds / 30)),
        str(round((activity.distance_meters or 0) / 100)),
    ))
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:24]


def _quality(activity: NormalizedActivity) -> tuple[int, int]:
    """Priorise le parcours sans friction, puis la richesse facultative."""
    is_fit = bool(activity.raw_metadata.get("source_file"))
    detail = (
        len(activity.samples)
        + len(activity.raw_metadata.get("laps", [])) * 10
    )
    if activity.provider == "health_connect":
        priority = 400
    elif is_fit:
        priority = 300
    elif activity.provider == "strava":
        priority = 200
    else:
        priority = 100
    return priority, detail


def merge_activities(current: NormalizedActivity, incoming: NormalizedActivity) -> NormalizedActivity:
    # À qualité égale, le réimport le plus récent corrige la version
    # précédente (distance, calories ou échantillons mis à jour).
    winner, fallback = (
        (incoming, current)
        if _quality(incoming) >= _quality(current)
        else (current, incoming)
    )
    merged = NormalizedActivity(**winner.to_dict())
    merged.canonical_id = current.canonical_id or incoming.canonical_id or activity_fingerprint(winner)
    merged.source_ids = {**current.source_ids, current.provider: current.external_id,
                         **incoming.source_ids, incoming.provider: incoming.external_id}
    ignored = {"provider", "external_id", "source_ids", "field_provenance", "canonical_id",
               "raw_metadata", "samples", "imported_at"}
    provenance = {**fallback.field_provenance, **winner.field_provenance}
    for item in fields(NormalizedActivity):
        name = item.name
        if name in ignored:
            continue
        if getattr(merged, name) in (None, "", [], {}):
            setattr(merged, name, getattr(fallback, name))
            if getattr(merged, name) not in (None, "", [], {}):
                provenance[name] = fallback.provider
        elif name not in provenance:
            provenance[name] = winner.provider
    merged.raw_metadata = {
        **fallback.raw_metadata,
        **winner.raw_metadata,
    }

    # Health Connect reste la référence quotidienne, mais un FIT disponible
    # peut enrichir l'analyse avec ses points 1 Hz, ses tours, son GPS et ses
    # dynamiques sans remplacer les totaux issus du téléphone.
    fallback_is_fit = bool(
        fallback.raw_metadata.get("source_file")
    )
    if (
        winner.provider == "health_connect"
        and fallback_is_fit
        and len(fallback.samples) > len(winner.samples)
    ):
        merged.samples = list(fallback.samples)
        provenance["samples"] = "garmin_fit"
    else:
        provenance.setdefault("samples", winner.provider)

    merged.field_provenance = provenance
    return merged


class ActivityStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[NormalizedActivity]:
        if not self.path.is_file():
            return []
        loaded = []
        for item in json.loads(self.path.read_text(encoding="utf-8")):
            payload = dict(item)
            payload["samples"] = [
                sample if isinstance(sample, ActivitySample) else ActivitySample(**sample)
                for sample in payload.get("samples", [])
                if isinstance(sample, (dict, ActivitySample))
            ]
            loaded.append(NormalizedActivity(**payload))
        return loaded

    def ingest(self, activities: Iterable[NormalizedActivity]) -> list[NormalizedActivity]:
        indexed = {}
        source_index = {}

        for activity in [*self.load(), *activities]:
            activity.source_ids = {
                **activity.source_ids,
                activity.provider: activity.external_id,
            }
            source_keys = {
                (str(provider), str(external_id))
                for provider, external_id in activity.source_ids.items()
                if provider and external_id
            }
            existing_key = next(
                (
                    source_index[source_key]
                    for source_key in source_keys
                    if source_key in source_index
                ),
                None,
            )
            fingerprint_key = (
                activity.canonical_id
                or activity_fingerprint(activity)
            )
            key = existing_key or fingerprint_key

            if (
                existing_key is not None
                and fingerprint_key != existing_key
                and fingerprint_key in indexed
            ):
                activity = merge_activities(
                    indexed.pop(fingerprint_key),
                    activity,
                )
            activity.canonical_id = key
            indexed[key] = (
                merge_activities(indexed[key], activity)
                if key in indexed else activity
            )
            indexed[key].canonical_id = key
            for provider, external_id in indexed[key].source_ids.items():
                if provider and external_id:
                    source_index[
                        (str(provider), str(external_id))
                    ] = key

        result = sorted(indexed.values(), key=lambda item: item.start_time)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps([item.to_dict() for item in result], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
        return result
