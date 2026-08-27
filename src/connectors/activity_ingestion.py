"""Stockage idempotent et fusion multi-source des activités Atlas."""

from dataclasses import fields
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .activity_schema import NormalizedActivity


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
    is_fit = bool(activity.raw_metadata.get("source_file"))
    detail = len(activity.samples) + len(activity.raw_metadata.get("laps", [])) * 10
    return (300 if is_fit else 200 if activity.provider == "strava" else 100, detail)


def merge_activities(current: NormalizedActivity, incoming: NormalizedActivity) -> NormalizedActivity:
    winner, fallback = (incoming, current) if _quality(incoming) > _quality(current) else (current, incoming)
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
    merged.field_provenance = provenance
    merged.raw_metadata = {**fallback.raw_metadata, **winner.raw_metadata}
    return merged


class ActivityStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[NormalizedActivity]:
        if not self.path.is_file():
            return []
        return [NormalizedActivity(**item) for item in json.loads(self.path.read_text(encoding="utf-8"))]

    def ingest(self, activities: Iterable[NormalizedActivity]) -> list[NormalizedActivity]:
        indexed = {}
        for activity in [*self.load(), *activities]:
            key = activity.canonical_id or activity_fingerprint(activity)
            activity.canonical_id = key
            activity.source_ids = {**activity.source_ids, activity.provider: activity.external_id}
            indexed[key] = merge_activities(indexed[key], activity) if key in indexed else activity
        result = sorted(indexed.values(), key=lambda item: item.start_time)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps([item.to_dict() for item in result], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
        return result
