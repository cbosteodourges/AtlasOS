"""Invariants de sécurité appliqués aux comptes rendus d'entraînement."""

from __future__ import annotations

from typing import Any


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def validate_execution_report(report: dict[str, Any]) -> dict[str, Any]:
    """Contrôle la cohérence structurelle et les analyses autorisées."""
    activity = report.get("activity") or {}
    analysis = report.get("analysis") or {}
    match = report.get("workout_match") or {}
    execution = match.get("execution") or {}
    intervals = execution.get("interval_details") or []
    blocks = analysis.get("blocks") or []
    errors: list[str] = []
    warnings: list[str] = []

    completed = _number(execution.get("completed_repetition_count"))
    if intervals and completed is not None and len(intervals) != round(completed):
        errors.append(
            "Le nombre de fractions détaillées ne correspond pas au nombre annoncé."
        )

    previous_end: float | None = None
    for index, interval in enumerate(intervals, start=1):
        duration = _number(interval.get("duration_seconds"))
        start = _number(interval.get("start_seconds"))
        end = _number(interval.get("end_seconds"))
        if duration is None or duration <= 0:
            errors.append(f"La fraction {index} possède une durée invalide.")
        if start is not None and end is not None:
            if end <= start:
                errors.append(f"La fraction {index} possède des bornes invalides.")
            if previous_end is not None and start < previous_end:
                errors.append("Les fractions se chevauchent dans la chronologie.")
            previous_end = end

    activity_seconds = (_number(activity.get("duration_minutes")) or 0) * 60
    ordered_phases = sorted(
        (
            (_number(block.get("start_offset_seconds")),
             _number(block.get("end_offset_seconds")))
            for block in blocks
        ),
        key=lambda item: item[0] if item[0] is not None else float("inf"),
    )
    previous_phase_end: float | None = None
    for start, end in ordered_phases:
        if start is None or end is None or end <= start:
            errors.append("Une phase possède des bornes temporelles invalides.")
            continue
        if previous_phase_end is None and start > 15:
            errors.append("La chronologie ne commence pas au début de l’activité.")
        elif previous_phase_end is not None:
            if start < previous_phase_end - 2:
                errors.append("Des phases se chevauchent dans la chronologie.")
            elif start > previous_phase_end + 15:
                errors.append("Un intervalle manque dans la chronologie des phases.")
        previous_phase_end = max(previous_phase_end or end, end)
    phase_ends = [
        value for value in (
            _number(block.get("end_offset_seconds")) for block in blocks
        ) if value is not None
    ]
    if activity_seconds > 0 and phase_ends:
        timeline_end = max(phase_ends)
        difference = abs(timeline_end - activity_seconds)
        if difference > 15:
            errors.append(
                "La chronologie des phases ne couvre pas la durée réelle de l’activité."
            )
        elif difference > 2:
            warnings.append(
                "La chronologie comporte un léger écart compatible avec l’échantillonnage."
            )

    speed_complete = bool(intervals) and all(
        (_number(item.get("average_speed_kmh")) or 0) > 0 for item in intervals
    )
    heart_rate_complete = bool(intervals) and all(
        (_number(item.get("average_heart_rate_bpm")) or 0) > 0 for item in intervals
    )
    recoveries_measured = len(intervals) > 1 and all(
        (_number(item.get("recovery_seconds")) or 0) > 0
        for item in intervals[:-1]
    )
    integrity = analysis.get("data_integrity") or {}
    heart_rate_available = integrity.get("heart_rate_available") is not False
    speed_available = integrity.get("speed_available") is not False
    heart_rate_reliable = integrity.get("heart_rate_reliable") is not False
    if heart_rate_complete and not heart_rate_reliable:
        warnings.append(
            "La fréquence cardiaque est présente mais signalée comme non fiable."
        )

    capabilities = {
        "interval_count": not any("nombre de fractions" in item for item in errors),
        "timeline": not any(
            "chronologie" in item.lower() or "phases se chevauchent" in item.lower()
            for item in errors
        ),
        "speed_regularity": speed_complete and speed_available,
        "heart_rate_evolution": (
            heart_rate_complete and heart_rate_available and heart_rate_reliable
        ),
        "recovery_interpretation": (
            recoveries_measured and heart_rate_available and heart_rate_reliable
        ),
    }
    status = "error" if errors else "warning" if warnings else "valid"
    return {
        "status": status,
        "safe_for_interpretation": not errors,
        "capabilities": capabilities,
        "errors": errors,
        "warnings": warnings,
    }
