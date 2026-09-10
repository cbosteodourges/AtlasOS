"""Lecture physiologique prudente des séances fractionnées."""

from __future__ import annotations

from statistics import median
from typing import Any


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _family(report: dict[str, Any]) -> str:
    analysis = report.get("analysis") or {}
    value = str(
        analysis.get("session_type") or analysis.get("dominant_work_type") or ""
    ).lower()
    if any(token in value for token in ("vma", "vo2", "vo₂")):
        return "vo2"
    if any(token in value for token in ("sv2", "threshold", "seuil")):
        return "threshold"
    return "interval"


def interpret_interval_physiology(report: dict[str, Any]) -> dict[str, Any]:
    """Décrit seulement les phénomènes soutenus par les métriques transmises."""
    execution = ((report.get("workout_match") or {}).get("execution") or {})
    intervals = execution.get("interval_details") or []
    family = _family(report)
    if len(intervals) < 2:
        return {
            "status": "unavailable",
            "family": family,
            "confidence": 0,
            "title": "Analyse des fractions en construction",
            "observations": [],
            "limitations": ["Au moins deux fractions complètes sont nécessaires."],
        }

    speeds = [_number(item.get("average_speed_kmh")) for item in intervals]
    heart_rates = [_number(item.get("average_heart_rate_bpm")) for item in intervals]
    recovery_drops = [
        _number(item.get("recovery_heart_rate_drop_bpm"))
        for item in intervals[:-1]
    ]
    integrity = (report.get("analysis") or {}).get("data_integrity") or {}
    heart_rate_available = integrity.get("heart_rate_available") is not False
    speed_available = integrity.get("speed_available") is not False
    heart_rate_reliable = integrity.get("heart_rate_reliable") is not False
    observations: list[str] = []
    limitations: list[str] = []
    metrics: dict[str, Any] = {}

    complete_speeds = speed_available and all(
        value is not None and value > 0 for value in speeds
    )
    if complete_speeds:
        valid_speeds = [float(value) for value in speeds if value is not None]
        paces = [3600 / value for value in valid_speeds]
        pace_spread = max(paces) - min(paces)
        speed_change = (valid_speeds[-1] / valid_speeds[0] - 1) * 100
        metrics.update({
            "pace_spread_seconds_per_km": round(pace_spread, 1),
            "first_to_last_speed_change_percent": round(speed_change, 1),
        })
        if pace_spread <= 20:
            observations.append(
                f"Les fractions sont régulières, avec {pace_spread:.0f} s/km d’écart."
            )
        else:
            observations.append(
                f"L’écart entre les fractions atteint {pace_spread:.0f} s/km."
            )
        if speed_change >= 3:
            observations.append(
                f"La dernière fraction est {speed_change:.1f} % plus rapide que la première."
            )
            title = "Une série terminée en progression"
        elif speed_change <= -3:
            observations.append(
                f"La dernière fraction est {abs(speed_change):.1f} % moins rapide que la première."
            )
            title = "Une baisse d’allure à replacer dans le contexte"
        else:
            title = "Une allure maintenue jusqu’au dernier bloc"
    else:
        title = "Une série reconnue avec une vitesse incomplète"
        limitations.append(
            "La vitesse n’est pas disponible sur toutes les fractions ; la régularité n’est pas interprétée."
        )

    complete_hr = all(value is not None and value > 0 for value in heart_rates)
    if complete_hr and heart_rate_available and heart_rate_reliable:
        valid_hr = [float(value) for value in heart_rates if value is not None]
        heart_rate_change = valid_hr[-1] - valid_hr[0]
        metrics["first_to_last_heart_rate_change_bpm"] = round(heart_rate_change, 1)
        observations.append(
            f"La fréquence cardiaque évolue de {heart_rate_change:+.0f} bpm entre la première et la dernière fraction."
        )
    elif not complete_hr or not heart_rate_available:
        limitations.append(
            "La fréquence cardiaque n’est pas disponible sur toutes les fractions."
        )
    else:
        limitations.append(
            "La fréquence cardiaque transmise est signalée comme non fiable."
        )

    complete_recovery_drops = bool(recovery_drops) and all(
        value is not None and value >= 0 for value in recovery_drops
    )
    if complete_recovery_drops and heart_rate_available and heart_rate_reliable:
        valid_drops = [float(value) for value in recovery_drops if value is not None]
        median_drop = median(valid_drops)
        metrics["median_recovery_heart_rate_drop_bpm"] = round(median_drop, 1)
        observations.append(
            f"La baisse cardiaque médiane pendant les récupérations est de {median_drop:.0f} bpm."
        )
    else:
        limitations.append(
            "La baisse cardiaque n’est pas mesurable sur toutes les récupérations ; leur efficacité n’est pas conclue."
        )

    available_groups = sum((
        complete_speeds,
        complete_hr and heart_rate_available and heart_rate_reliable,
        complete_recovery_drops and heart_rate_available and heart_rate_reliable,
    ))
    confidence = min(95, 35 + len(intervals) * 4 + available_groups * 12)
    return {
        "status": "available",
        "family": family,
        "confidence": confidence,
        "title": title,
        "observations": observations,
        "limitations": limitations,
        "metrics": metrics,
        "guardrail": (
            "Cette lecture décrit l’exécution de la séance et ne constitue pas, seule, "
            "une modification du niveau physiologique."
        ),
    }
