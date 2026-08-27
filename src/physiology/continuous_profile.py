"""Ajustement longitudinal prudent de VO2max, VMA, SV1 et SV2."""

from __future__ import annotations
from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bounded(previous: float | None, estimate: float, daily_change: float) -> float:
    if previous is None:
        return estimate
    return max(previous - daily_change, min(previous + daily_change, estimate))


class ContinuousPhysiologyEstimator:
    """Estime des tendances ; ne remplace pas une mesure de laboratoire."""

    def estimate(self, activities: Iterable[Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
        current = current or {}
        declared_maximum_hr = _number(current.get("maximum_heart_rate_bpm"))
        usable_hr_ceiling = declared_maximum_hr or 220
        runs = [item for item in activities if str(getattr(item, "activity_type", "")).lower() in {"run", "running", "trail_running", "56"}]
        speeds = []
        threshold_speeds = []
        threshold_hr = []
        for activity in runs:
            samples = getattr(activity, "samples", []) or []
            sample_speeds = [_number(getattr(sample, "speed_mps", None)) for sample in samples]
            sample_speeds = [value * 3.6 for value in sample_speeds if value and 4 <= value * 3.6 <= 30]
            # Une pointe de quelques secondes ne vaut pas une VMA. Il faut au
            # minimum trois minutes de vitesse soutenue ; au-delà, Atlas vise
            # une fenêtre de quatre à six minutes selon la séance disponible.
            if len(sample_speeds) >= 180:
                window = max(180, min(360, len(sample_speeds) // 4))
                sustained = max(median(sample_speeds[index:index + window]) for index in range(0, len(sample_speeds) - window + 1, max(1, window // 5)))
                speeds.append(sustained)
            average = _number(getattr(activity, "average_speed_mps", None))
            duration = _number(getattr(activity, "duration_seconds", None)) or 0
            heart_rate = _number(getattr(activity, "average_heart_rate_bpm", None))
            # Une allure moyenne d'endurance ne constitue pas une observation
            # de seuil. Atlas ne la retient que si la FC confirme un effort
            # soutenu, et ignore les FC > 170 tant qu'elles ne sont pas validées.
            if average and duration >= 900 and heart_rate and 145 <= heart_rate <= usable_hr_ceiling:
                threshold_speeds.append(average * 3.6)
                threshold_hr.append(heart_rate)
        evidence = len(runs) + len(speeds) * 2
        confidence = min(.95, .18 + evidence * .07)
        if not runs or confidence < .32:
            return {"updated": False, "confidence": round(confidence, 2), "evidence_sessions": len(runs),
                    "reason": "Historique de course encore insuffisant."}
        observed_vma = max(speeds) if speeds else max(threshold_speeds, default=0) * 1.10
        if not observed_vma:
            return {"updated": False, "confidence": round(confidence, 2), "evidence_sessions": len(runs),
                    "reason": "Aucune vitesse exploitable."}
        observed_vma = max(7, min(25, observed_vma))
        observed_sv2 = median(sorted(threshold_speeds)[-5:]) if threshold_speeds else observed_vma * .88
        observed_sv2 = max(observed_vma * .78, min(observed_vma * .94, observed_sv2))
        observed_sv1 = observed_sv2 * .82
        old_vma = _number(current.get("vma_kmh") or current.get("vma_training_reference_kmh"))
        old_vo2 = _number(current.get("vo2_max"))
        sv1_current = current.get("sv1") or {}
        sv2_current = current.get("sv2") or {}
        vma = round(_bounded(old_vma, observed_vma, .2), 2)
        vo2 = round(_bounded(old_vo2, 3.5 * vma, .7), 1)
        sv1 = round(_bounded(_number(sv1_current.get("speed_kmh")), observed_sv1, .15), 2)
        sv2 = round(_bounded(_number(sv2_current.get("speed_kmh")), observed_sv2, .15), 2)
        sv2_hr = round(_bounded(_number(sv2_current.get("heart_rate_bpm")), median(threshold_hr), 2)) if threshold_hr else sv2_current.get("heart_rate_bpm")
        maximum_hr = declared_maximum_hr
        sv1_hr = sv1_current.get("heart_rate_bpm")
        if sv1_hr is None and maximum_hr:
            sv1_hr = round(maximum_hr * .81)
        return {"updated": True, "confidence": round(confidence, 2), "evidence_sessions": len(runs),
                "updated_at": datetime.now(timezone.utc).isoformat(), "method": "tendance terrain bornée",
                "vo2_max": vo2, "vma_kmh": vma, "vma_training_reference_kmh": vma,
                "sv1": {"speed_kmh": sv1, "heart_rate_bpm": sv1_hr, "status": "longitudinal_estimate"},
                "sv2": {"speed_kmh": sv2, "heart_rate_bpm": sv2_hr, "status": "longitudinal_estimate"},
                "observed": {"vma_kmh": round(observed_vma, 2), "sv2_speed_kmh": round(observed_sv2, 2)},
                "maximum_heart_rate_bpm": maximum_hr,
                "warning": "Estimation d’entraînement, non mesure médicale. Les valeurs supérieures à la FC maximale déclarée sont conservées dans les données brutes mais exclues du recalibrage."}
