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
    """Priorise la source sportive la plus précise, puis sa richesse."""
    is_fit = bool(activity.raw_metadata.get("source_file"))
    detail = (
        len(activity.samples)
        + len(activity.raw_metadata.get("laps", [])) * 10
    )
    if is_fit:
        priority = 500
    elif activity.provider == "health_connect":
        priority = 400
    elif activity.provider == "strava":
        priority = 200
    else:
        priority = 100
    return priority, detail


def _provenance_label(activity: NormalizedActivity) -> str:
    return (
        "garmin_fit"
        if activity.raw_metadata.get("source_file")
        else activity.provider
    )


def _same_session(left: NormalizedActivity, right: NormalizedActivity) -> bool:
    """Tolère les petits écarts de résumé entre deux connecteurs."""
    if left.activity_type.lower() != right.activity_type.lower():
        return False
    left_start = datetime.fromisoformat(left.start_time.replace("Z", "+00:00"))
    right_start = datetime.fromisoformat(right.start_time.replace("Z", "+00:00"))
    if abs((left_start - right_start).total_seconds()) > 120:
        return False
    duration_limit = max(90.0, max(left.duration_seconds, right.duration_seconds) * .03)
    if abs(left.duration_seconds - right.duration_seconds) > duration_limit:
        return False
    if left.distance_meters and right.distance_meters:
        distance_limit = max(500.0, max(left.distance_meters, right.distance_meters) * .05)
        if abs(left.distance_meters - right.distance_meters) > distance_limit:
            return False
    return True


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
    winner_source = _provenance_label(winner)
    fallback_source = _provenance_label(fallback)
    provenance = {**fallback.field_provenance, **winner.field_provenance}
    for item in fields(NormalizedActivity):
        name = item.name
        if name in ignored:
            continue
        if getattr(merged, name) in (None, "", [], {}):
            setattr(merged, name, getattr(fallback, name))
            if getattr(merged, name) not in (None, "", [], {}):
                provenance[name] = fallback_source
        elif name not in provenance:
            provenance[name] = winner_source
    merged.raw_metadata = {
        **fallback.raw_metadata,
        **winner.raw_metadata,
    }

    # Le FIT est la référence sportive fine. Health Connect conserve son
    # identifiant et complète seulement les champs réellement absents.
    fallback_is_fit = bool(
        fallback.raw_metadata.get("source_file")
    )
    enrichment_source = (
        "garmin_fit"
        if fallback_is_fit
        else "strava"
        if fallback.provider == "strava"
        else None
    )
    if (
        winner.provider == "health_connect"
        and enrichment_source
        and len(fallback.samples) > len(winner.samples)
    ):
        merged.samples = list(fallback.samples)
        provenance["samples"] = enrichment_source
    else:
        provenance.setdefault("samples", winner_source)

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
            if existing_key is None:
                existing_key = next(
                    (
                        candidate_key
                        for candidate_key, candidate in indexed.items()
                        if _same_session(candidate, activity)
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
