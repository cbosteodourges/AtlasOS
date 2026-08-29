"""Indice de récupération Atlas explicable, utilisable avec ou sans VFC."""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Iterable


def _dt(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_sleep_duration(hours: float, target_hours: float) -> float:
    """Évalue la nuit par rapport au besoin personnel, pas à un seuil universel."""
    target = max(7.5, min(9.0, target_hours))
    if hours < target:
        return max(0, 100 - (target - hours) * 30)
    if hours <= target + 1:
        return 100
    return max(45, 100 - (hours - target - 1) * 10)


def _baseline(values: list[float], fallback: float | None = None) -> float | None:
    return mean(values[-28:]) if len(values) >= 3 else fallback


class AtlasRecoveryIndex:
    """Construit un score transparent sans fabriquer de VFC absente."""

    def build(self, wellness: Iterable[dict[str, Any]], activities: Iterable[Any]) -> dict[str, Any]:
        records = [item for item in wellness if isinstance(item, dict)]
        sleeps = [item for item in records if item.get("type") == "sleep"]
        resting = [item for item in records if item.get("type") == "resting_heart_rate"]
        hrv = [item for item in records if item.get("type") == "hrv_rmssd"]
        heart_series = [item for item in records if item.get("type") == "heart_rate_series"]
        by_day: dict[str, dict[str, Any]] = {}
        resting_values: list[float] = []
        hrv_values: list[float] = []
        sleep_duration_values: list[float] = []
        daily_load: dict[str, float] = defaultdict(float)
        for activity in activities:
            stamp = _dt(getattr(activity, "start_time", None))
            if not stamp:
                continue
            explicit = _number(getattr(activity, "training_load", None))
            duration = (_number(getattr(activity, "duration_seconds", None)) or 0) / 60
            heart_rate = _number(getattr(activity, "average_heart_rate_bpm", None))
            derived = duration * (1 + max(0, (heart_rate or 120) - 120) / 50)
            daily_load[stamp.date().isoformat()] += explicit if explicit is not None else derived

        for sleep in sorted(sleeps, key=lambda item: str(item.get("end_time"))):
            start, end = _dt(sleep.get("start_time")), _dt(sleep.get("end_time"))
            if not start or not end or end <= start:
                continue
            day = end.date().isoformat()
            duration = (end - start).total_seconds()
            stages = defaultdict(float)
            for stage in sleep.get("stages", []):
                stage_start, stage_end = _dt(stage.get("start_time")), _dt(stage.get("end_time"))
                if stage_start and stage_end and stage_end > stage_start:
                    stages[str(stage.get("stage"))] += (stage_end - stage_start).total_seconds()
            sleep_hr = []
            for series in heart_series:
                for sample in series.get("samples", []):
                    stamp, value = _dt(sample.get("timestamp")), _number(sample.get("value"))
                    if stamp and value is not None and start <= stamp <= end:
                        sleep_hr.append(value)
            resting_today = [(_dt(item.get("start_time")), _number(item.get("value"))) for item in resting]
            resting_today = [value for stamp, value in resting_today if stamp and stamp.date() == end.date() and value is not None]
            hrv_today = [(_dt(item.get("start_time")), _number(item.get("value"))) for item in hrv]
            hrv_today = [value for stamp, value in hrv_today if stamp and stamp.date() == end.date() and value is not None]
            resting_value = mean(resting_today) if resting_today else None
            hrv_value = mean(hrv_today) if hrv_today else None
            rest_base = _baseline(resting_values, resting_value)
            hrv_base = _baseline(hrv_values, hrv_value)
            sleep_hours = duration / 3600
            sleep_target = _baseline(sleep_duration_values, 8.0) or 8.0
            sleep_target = max(7.5, min(9.0, sleep_target))
            components = [{"key": "sleep_duration", "label": "Durée du sommeil",
                           "score": _score_sleep_duration(sleep_hours, sleep_target),
                           "weight": 35, "value": round(sleep_hours, 2), "unit": "h",
                           "personal_target_hours": round(sleep_target, 2),
                           "difference_minutes": round((sleep_hours - sleep_target) * 60)}]
            known = sum(stages.values())
            if known:
                deep = stages.get("5", 0) / duration
                rem = stages.get("6", 0) / duration
                awake = (stages.get("1", 0) + stages.get("7", 0)) / duration
                stage_score = max(0, min(100, 100 - abs(deep - .2) * 170 - abs(rem - .23) * 140 - max(0, awake - .1) * 180))
                components.append({"key": "sleep_stages", "label": "Architecture du sommeil",
                                   "score": stage_score, "weight": 25,
                                   "deep_percent": round(deep * 100), "rem_percent": round(rem * 100),
                                   "awake_percent": round(awake * 100)})
            if resting_value is not None:
                difference = resting_value - (rest_base or resting_value)
                components.append({"key": "resting_hr", "label": "Fréquence cardiaque au repos",
                                   "score": max(0, min(100, 82 - difference * 7)), "weight": 20,
                                   "value": round(resting_value), "baseline": round(rest_base or resting_value, 1), "unit": "bpm"})
            if sleep_hr:
                nocturnal = mean(sleep_hr)
                components.append({"key": "night_hr", "label": "Fréquence cardiaque nocturne",
                                   "score": max(20, min(100, 105 - nocturnal)), "weight": 15,
                                   "value": round(nocturnal, 1), "unit": "bpm"})
            if hrv_value is not None:
                ratio = hrv_value / max(hrv_base or hrv_value, 1)
                components.append({"key": "hrv", "label": "VFC RMSSD mesurée",
                                   "score": max(0, min(100, 75 + (ratio - 1) * 100)), "weight": 15,
                                   "value": round(hrv_value, 1), "baseline": round(hrv_base or hrv_value, 1), "unit": "ms"})
            wake_day = end.date()
            acute = sum(daily_load.get((wake_day - timedelta(days=offset)).isoformat(), 0) for offset in range(1, 8))
            chronic_total = sum(daily_load.get((wake_day - timedelta(days=offset)).isoformat(), 0) for offset in range(1, 29))
            if chronic_total > 0:
                ratio = acute / max(chronic_total / 4, 1)
                load_score = 92 if .8 <= ratio <= 1.3 else 65 if .6 <= ratio <= 1.5 else 38
                components.append({"key": "training_load", "label": "Charge récente",
                                   "score": load_score, "weight": 15,
                                   "acute_chronic_ratio": round(ratio, 2)})
            total_weight = sum(item["weight"] for item in components)
            score = round(sum(item["score"] * item["weight"] for item in components) / total_weight)
            confidence = round(min(
                95 if hrv_value is not None else 90,
                25 + len(components) * 12
                + min(20, len(sleep_duration_values))
                + min(10, len(resting_values)),
            ))
            by_day[day] = {"day": day, "atlas_recovery_index": score,
                           "atlas_index": score, "confidence": confidence,
                           "components": components, "hrv_used": hrv_value is not None,
                           "explanation": "Score fondé uniquement sur les mesures disponibles ; les poids sont redistribués quand la VFC manque."}
            sleep_duration_values.append(sleep_hours)
            if resting_value is not None:
                resting_values.append(resting_value)
            if hrv_value is not None:
                hrv_values.append(hrv_value)
        history = [by_day[key] for key in sorted(by_day)]
        return {"latest": history[-1] if history else None, "history": history,
                "generated_at": datetime.now(timezone.utc).isoformat()}
