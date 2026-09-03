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


INTENSITY_FAMILIES = {
    "tempo": {
        "label": "Tempo",
        "short": "Z3",
        "tokens": ("tempo", "z3", "steady"),
        "block_tokens": ("tempo", "z3", "steady"),
        "minimum_work_minutes": 12,
        "metric": "efficiency",
    },
    "threshold": {
        "label": "Seuil",
        "short": "SV2",
        "tokens": ("sv2", "threshold", "seuil"),
        "block_tokens": ("sv2", "threshold", "seuil"),
        "minimum_work_minutes": 8,
        "metric": "efficiency",
    },
    "vo2": {
        "label": "Puissance aérobie",
        "short": "VO₂max",
        "tokens": ("vma", "vo2", "vo₂", "max_aerobic"),
        "block_tokens": ("vma", "vo2", "vo₂", "max_aerobic"),
        "minimum_work_minutes": 4,
        "metric": "speed",
    },
}


def _weighted_block_metrics(
    item: dict[str, Any],
    block_tokens: tuple[str, ...],
) -> tuple[float | None, float | None, float | None, int]:
    blocks = (item.get("analysis") or {}).get("blocks") or []
    selected = []
    for block in blocks:
        block_type = str(block.get("block_type") or "").lower()
        if any(token in block_type for token in block_tokens):
            duration = _number(block.get("duration_seconds"))
            speed = _number(block.get("average_speed_kmh"))
            heart_rate = _number(block.get("average_heart_rate_bpm"))
            if duration and duration > 0 and speed:
                selected.append((duration, speed, heart_rate))
    if not selected:
        return None, None, None, 0
    duration = sum(value[0] for value in selected)
    speed = sum(value[0] * value[1] for value in selected) / duration
    hr_values = [value for value in selected if value[2] is not None]
    heart_rate = (
        sum(value[0] * value[2] for value in hr_values)
        / sum(value[0] for value in hr_values)
        if hr_values else None
    )
    return speed, heart_rate, duration / 60, len(selected)


def build_intensity_progression(
    summaries: list[dict[str, Any]],
    family: str,
) -> dict[str, Any]:
    """Compare Z3, SV2 ou VO₂max à partir des seuls blocs de travail."""
    if family not in INTENSITY_FAMILIES:
        raise ValueError(f"Filière non prise en charge : {family}")
    config = INTENSITY_FAMILIES[family]
    accepted: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()

    for item in summaries:
        activity = item.get("activity") or {}
        if str(activity.get("sport") or "").lower() not in {
            "running", "run", "road_running", "trail",
        }:
            continue
        descriptor = _descriptor(item)
        if not any(token in descriptor for token in config["tokens"]):
            continue
        integrity = (item.get("analysis") or {}).get("data_integrity") or {}
        if integrity.get("physiological_data_usable") is False:
            rejected["données physiologiques non fiables"] += 1
            continue
        day = _day(item.get("start_time"))
        quality = _number(activity.get("data_quality_score"))
        if day is None or (quality is not None and quality < 50):
            rejected["qualité insuffisante"] += 1
            continue

        speed, heart_rate, work_minutes, repetitions = _weighted_block_metrics(
            item, config["block_tokens"],
        )
        # Les anciens FIT tempo peuvent ne pas disposer de tours détaillés.
        # On accepte alors la partie de travail agrégée, jamais la séance
        # entière pour le SV2 ou la VO₂max.
        analysis = item.get("analysis") or {}
        if speed is None and family == "tempo":
            work_seconds = _number(analysis.get("work_duration_seconds"))
            work_distance = _number(analysis.get("work_distance_meters"))
            if work_seconds and work_distance:
                speed = work_distance / work_seconds * 3.6
                work_minutes = work_seconds / 60
                heart_rate = _number(activity.get("average_heart_rate_bpm"))
                repetitions = 1
        if speed is None or work_minutes is None:
            rejected["blocs de travail absents"] += 1
            continue
        if work_minutes < config["minimum_work_minutes"] or not 6 <= speed <= 24:
            rejected["travail spécifique insuffisant"] += 1
            continue
        if heart_rate is not None and not 80 <= heart_rate <= 205:
            heart_rate = None
        accepted.append({
            "day": day,
            "speed_kmh": speed,
            "heart_rate_bpm": heart_rate,
            "work_minutes": work_minutes,
            "repetitions": repetitions,
            "quality": quality,
        })

    accepted.sort(key=lambda item: item["day"])
    if accepted:
        reference_work = _median(item["work_minutes"] for item in accepted)
        protocol = [
            item for item in accepted
            if reference_work * .65 <= item["work_minutes"] <= reference_work * 1.35
        ]
        rejected["protocole trop différent"] += len(accepted) - len(protocol)
        accepted = protocol
    reference_hr_values = [
        item["heart_rate_bpm"] for item in accepted
        if item["heart_rate_bpm"] is not None
    ]
    reference_hr = _median(reference_hr_values) if reference_hr_values else None
    if reference_hr is not None and config["metric"] == "efficiency":
        comparable = [
            item for item in accepted
            if item["heart_rate_bpm"] is not None
            and abs(item["heart_rate_bpm"] - reference_hr) <= 15
        ]
        rejected["réponse cardiaque non comparable"] += len(accepted) - len(comparable)
        accepted = comparable

    for item in accepted:
        item["metric"] = (
            item["speed_kmh"] / item["heart_rate_bpm"]
            if config["metric"] == "efficiency" else item["speed_kmh"]
        )
    count = len(accepted)
    points = [{
        "day": item["day"],
        "work_speed_kmh": round(item["speed_kmh"], 2),
        "work_heart_rate_bpm": (
            round(item["heart_rate_bpm"])
            if item["heart_rate_bpm"] is not None else None
        ),
        "work_minutes": round(item["work_minutes"], 1),
        "repetitions": item["repetitions"],
    } for item in accepted]
    result = {
        "family": family,
        "label": config["label"],
        "short": config["short"],
        "available": count >= 4,
        "session_count": count,
        "points": points,
        "excluded": sum(rejected.values()),
        "exclusion_reasons": dict(rejected),
        "reference_heart_rate_bpm": round(reference_hr) if reference_hr else None,
        "trend": "insufficient",
        "trend_percent": None,
        "confidence": min(95, 25 + count * 7),
        "headline": f"Historique {config['short']} en construction",
        "summary": f"{count} séance(s) comparable(s) ; quatre sont nécessaires pour conclure.",
    }
    if count < 4:
        return result

    window = min(5, count // 2)
    early = accepted[:window]
    recent = accepted[-window:]
    early_metric = _median(item["metric"] for item in early)
    recent_metric = _median(item["metric"] for item in recent)
    change = (recent_metric / early_metric - 1) * 100
    trend = "up" if change >= 1.5 else ("down" if change <= -1.5 else "stable")
    early_speed = (
        early_metric * reference_hr
        if config["metric"] == "efficiency" else _median(item["speed_kmh"] for item in early)
    )
    recent_speed = (
        recent_metric * reference_hr
        if config["metric"] == "efficiency" else _median(item["speed_kmh"] for item in recent)
    )
    early_hr = [item["heart_rate_bpm"] for item in early if item["heart_rate_bpm"] is not None]
    recent_hr = [item["heart_rate_bpm"] for item in recent if item["heart_rate_bpm"] is not None]
    quality = [item["quality"] for item in accepted if item["quality"] is not None]
    confidence = min(95, round(38 + min(32, count * 4) + (_median(quality) if quality else 50) * .2))
    result.update({
        "trend": trend,
        "trend_percent": round(change, 1),
        "confidence": confidence,
        "headline": f"{config['label']} : " + {"up": "progression", "stable": "maintien", "down": "régression"}[trend],
        "summary": (
            f"Vitesse des blocs comparables : {early_speed:.2f} → {recent_speed:.2f} km/h "
            f"({change:+.1f} %)."
        ),
        "early": {
            "session_count": len(early), "work_speed_kmh": round(early_speed, 2),
            "heart_rate_bpm": round(_median(early_hr)) if early_hr else None,
            "from": early[0]["day"], "to": early[-1]["day"],
        },
        "recent": {
            "session_count": len(recent), "work_speed_kmh": round(recent_speed, 2),
            "heart_rate_bpm": round(_median(recent_hr)) if recent_hr else None,
            "from": recent[0]["day"], "to": recent[-1]["day"],
        },
        "method": (
            "Comparaison médiane des blocs de travail de protocoles proches. "
            + (
                "Vitesse ramenée à une réponse cardiaque commune."
                if config["metric"] == "efficiency"
                else "La vitesse des répétitions prime ; la FC reste contextuelle en VO₂max."
            )
        ),
    })
    return result


def build_tempo_progression(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return build_intensity_progression(summaries, "tempo")


def build_threshold_progression(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return build_intensity_progression(summaries, "threshold")


def build_vo2_progression(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return build_intensity_progression(summaries, "vo2")


def build_all_family_progressions(
    summaries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Prépare toutes les filières, sans imposer leur intégration à l'UI."""
    return {
        "endurance": build_endurance_progression(summaries),
        "tempo": build_tempo_progression(summaries),
        "threshold": build_threshold_progression(summaries),
        "vo2": build_vo2_progression(summaries),
    }
