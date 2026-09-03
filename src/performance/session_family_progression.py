"""Comparaison longitudinale de séances appartenant à une même filière."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from statistics import median
from typing import Any, Iterable


ENDURANCE_TOKENS = (
    "endurance", "easy", "recovery", "récupération", "z1", "z2",
)
NON_ENDURANCE_TOKENS = (
    "tempo", "z3", "sv1", "sv2", "threshold", "seuil", "vma",
    "vo2", "vo₂", "interval", "race", "competition", "compétition",
)


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _descriptor(item: dict[str, Any]) -> str:
    activity = item.get("activity") or {}
    analysis = item.get("analysis") or {}
    execution = (item.get("workout_match") or {}).get("execution") or {}
    return " ".join(str(value or "").lower() for value in (
        activity.get("session_type"), analysis.get("session_type"),
        analysis.get("dominant_work_type"), execution.get("workout_name"),
    ))


def _day(value: Any) -> str | None:
    text = str(value or "")[:10]
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return None
    return text


def _median(items: Iterable[float]) -> float:
    return float(median(list(items)))


def build_endurance_progression(
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Mesure l'évolution du rendement vitesse/FC des sorties Z1–Z2.

    Les séances rapides, vallonnées, trop courtes ou techniquement fragiles
    sont écartées. Aucun résultat directionnel n'est rendu avant quatre
    observations comparables.
    """
    accepted: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()

    for item in summaries:
        activity = item.get("activity") or {}
        sport = str(activity.get("sport") or "").lower()
        if sport not in {"running", "run", "road_running", "trail"}:
            continue
        descriptor = _descriptor(item)
        if (
            not any(token in descriptor for token in ENDURANCE_TOKENS)
            or any(token in descriptor for token in NON_ENDURANCE_TOKENS)
        ):
            continue

        speed = _number(activity.get("average_speed_kmh"))
        heart_rate = _number(activity.get("average_heart_rate_bpm"))
        duration = _number(activity.get("duration_minutes"))
        distance = _number(activity.get("distance_km"))
        elevation = _number(activity.get("elevation_gain_m"))
        quality = _number(activity.get("data_quality_score"))
        integrity = (item.get("analysis") or {}).get("data_integrity") or {}
        day = _day(item.get("start_time"))
        if None in {speed, heart_rate, duration, distance} or day is None:
            rejected["mesures manquantes"] += 1
            continue
        if duration < 25 or distance < 3:
            rejected["séance trop courte"] += 1
            continue
        if not 6 <= speed <= 16 or not 80 <= heart_rate <= 190:
            rejected["mesure hors plage"] += 1
            continue
        if quality is not None and quality < 50:
            rejected["qualité insuffisante"] += 1
            continue
        if integrity.get("heart_rate_reliable") is False:
            rejected["fréquence cardiaque non fiable"] += 1
            continue
        elevation_density = elevation / distance if elevation is not None else None
        if elevation_density is not None and elevation_density > 20:
            rejected["dénivelé trop important"] += 1
            continue

        drift = item.get("cardiac_drift") or {}
        decoupling = (
            _number(drift.get("aerobic_decoupling_percent"))
            if drift.get("analyzable") else None
        )
        accepted.append({
            "day": day,
            "speed_kmh": speed,
            "heart_rate_bpm": heart_rate,
            "efficiency": speed / heart_rate,
            "duration_minutes": duration,
            "distance_km": distance,
            "elevation_m_per_km": elevation_density,
            "drift_percent": decoupling,
            "quality": quality,
        })

    accepted.sort(key=lambda item: item["day"])
    reference_hr = (
        _median(item["heart_rate_bpm"] for item in accepted)
        if accepted else None
    )
    if reference_hr is not None:
        # Une FC très éloignée décrit une autre intensité, même si son libellé
        # FIT est « endurance ».
        comparable = [
            item for item in accepted
            if abs(item["heart_rate_bpm"] - reference_hr) <= 12
        ]
        rejected["intensité non comparable"] += len(accepted) - len(comparable)
        accepted = comparable

    points = []
    for item in accepted:
        points.append({
            "day": item["day"],
            "speed_kmh": round(item["speed_kmh"], 2),
            "heart_rate_bpm": round(item["heart_rate_bpm"]),
            "equivalent_speed_kmh": round(item["efficiency"] * reference_hr, 2),
            "drift_percent": (
                round(item["drift_percent"], 1)
                if item["drift_percent"] is not None else None
            ),
        })

    count = len(accepted)
    result = {
        "family": "endurance",
        "label": "Endurance fondamentale",
        "short": "Z1–Z2",
        "available": count >= 4,
        "session_count": count,
        "reference_heart_rate_bpm": round(reference_hr) if reference_hr else None,
        "points": points,
        "excluded": sum(rejected.values()),
        "exclusion_reasons": dict(rejected),
        "trend": "insufficient",
        "trend_percent": None,
        "confidence": min(95, 25 + count * 7),
        "headline": "Historique Z1–Z2 en construction",
        "summary": (
            f"{count} séance(s) comparable(s). Quatre sont nécessaires pour "
            "mesurer une évolution robuste."
        ),
    }
    if count < 4:
        return result

    window = min(5, count // 2)
    early = accepted[:window]
    recent = accepted[-window:]
    early_efficiency = _median(item["efficiency"] for item in early)
    recent_efficiency = _median(item["efficiency"] for item in recent)
    change = (recent_efficiency / early_efficiency - 1) * 100
    trend = "up" if change >= 1.5 else ("down" if change <= -1.5 else "stable")
    early_speed = early_efficiency * reference_hr
    recent_speed = recent_efficiency * reference_hr
    quality_values = [item["quality"] for item in accepted if item["quality"] is not None]
    drift_values = [item["drift_percent"] for item in recent if item["drift_percent"] is not None]
    confidence = min(
        95,
        round(38 + min(32, count * 4) + (_median(quality_values) if quality_values else 50) * .2),
    )
    wording = {"up": "progression", "stable": "maintien", "down": "régression"}[trend]
    direction = {"up": "plus vite", "stable": "à une allure stable", "down": "moins vite"}[trend]
    result.update({
        "trend": trend,
        "trend_percent": round(change, 1),
        "confidence": confidence,
        "headline": f"Endurance fondamentale : {wording}",
        "summary": (
            f"À {round(reference_hr)} bpm, vous courez {direction} : "
            f"{early_speed:.2f} → {recent_speed:.2f} km/h entre les deux fenêtres comparées."
        ),
        "early": {
            "session_count": len(early),
            "speed_at_reference_hr_kmh": round(early_speed, 2),
            "from": early[0]["day"],
            "to": early[-1]["day"],
        },
        "recent": {
            "session_count": len(recent),
            "speed_at_reference_hr_kmh": round(recent_speed, 2),
            "from": recent[0]["day"],
            "to": recent[-1]["day"],
            "median_drift_percent": round(_median(drift_values), 1) if drift_values else None,
        },
        "method": (
            "Médiane du rendement vitesse/FC, ramenée à une fréquence cardiaque "
            "personnelle commune. Séances vallonnées, courtes ou peu fiables exclues."
        ),
    })
    return result
