"""Comparaison prudente d'une séance avec sa propre famille historique."""

from __future__ import annotations

from statistics import median
from typing import Any, Iterable


RUNNING_SPORTS = {"running", "run", "road_running", "trail", "trail_running"}
CYCLING_SPORTS = {"cycling", "cycling_indoor", "indoor_cycling", "bike"}


def _text(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _sport_family(record: dict[str, Any]) -> str:
    activity = record.get("activity") or {}
    sport = _text(activity.get("sport") or record.get("sport"))
    if sport in RUNNING_SPORTS:
        return "running"
    if sport in CYCLING_SPORTS:
        return "cycling"
    return sport or "unknown"


def _session_family(record: dict[str, Any]) -> str:
    activity = record.get("activity") or {}
    analysis = record.get("analysis") or {}
    value = _text(
        analysis.get("session_type")
        or analysis.get("dominant_work_type")
        or activity.get("session_type")
        or record.get("session_type")
    )
    if any(token in value for token in ("vma", "vo2", "vo₂", "max_aerobic")):
        return "vo2"
    if any(token in value for token in ("sv2", "threshold", "seuil")):
        return "threshold"
    if any(token in value for token in ("tempo", "z3", "sub_threshold")):
        return "tempo"
    if any(token in value for token in ("endurance", "easy", "z1", "z2", "recovery")):
        return "endurance"
    if "long_run" in value or "sortie_longue" in value:
        return "long_run"
    return value or "unknown"


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _metrics(record: dict[str, Any]) -> dict[str, float | None]:
    activity = record.get("activity") or {}
    analysis = record.get("analysis") or {}
    blocks = analysis.get("blocks") or []
    family = _session_family(record)
    tokens = {
        "vo2": ("vma", "vo2"),
        "threshold": ("sv2", "threshold"),
        "tempo": ("z3", "tempo"),
    }.get(family, ())
    work = [
        block for block in blocks
        if not tokens or any(token in _text(block.get("block_type")) for token in tokens)
    ]
    speeds = [
        value for value in (_number(block.get("average_speed_kmh")) for block in work)
        if value is not None and value > 0
    ]
    heart_rates = [
        value for value in (_number(block.get("average_heart_rate_bpm")) for block in work)
        if value is not None and value > 0
    ]
    speed = median(speeds) if speeds else _number(activity.get("average_speed_kmh"))
    heart_rate = median(heart_rates) if heart_rates else _number(
        activity.get("average_heart_rate_bpm")
    )
    regularity = max(speeds) - min(speeds) if len(speeds) >= 2 else None
    recovery = _number(
        ((record.get("workout_match") or {}).get("execution") or {}).get(
            "recovery_compliance_score"
        )
    )
    return {
        "speed_kmh": speed,
        "heart_rate_bpm": heart_rate,
        "regularity_kmh": regularity,
        "recovery_score": recovery,
    }


def compare_with_similar_sessions(
    current: dict[str, Any],
    history: Iterable[dict[str, Any]],
    *,
    minimum_history: int = 2,
) -> dict[str, Any]:
    """Compare sans jamais mélanger sport ou famille physiologique."""
    sport = _sport_family(current)
    family = _session_family(current)
    comparable = [
        item for item in history
        if item is not current
        and _sport_family(item) == sport
        and _session_family(item) == family
    ]
    if len(comparable) < minimum_history:
        return {
            "status": "insufficient_history",
            "sport": sport,
            "family": family,
            "comparison_count": len(comparable),
            "message": "Pas encore assez de séances du même sport et de la même famille.",
        }
    current_metrics = _metrics(current)
    historical_metrics = [_metrics(item) for item in comparable]
    comparison: dict[str, Any] = {
        "status": "available",
        "sport": sport,
        "family": family,
        "comparison_count": len(comparable),
        "deltas": {},
    }
    for key, current_value in current_metrics.items():
        values = [item[key] for item in historical_metrics if item[key] is not None]
        if current_value is None or len(values) < minimum_history:
            comparison["deltas"][key] = None
            continue
        reference = median(values)
        comparison["deltas"][key] = {
            "current": round(current_value, 2),
            "reference": round(reference, 2),
            "difference": round(current_value - reference, 2),
        }
    return comparison
