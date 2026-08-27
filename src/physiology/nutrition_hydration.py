"""Synthèse nutrition et hydratation explicable pour Atlas."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any, Iterable


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class NutritionHydrationAnalyzer:
    """Agrège les mesures réelles sans interpréter une absence comme un déficit."""

    def analyze(self, records: Iterable[dict[str, Any]], *, weight_kg: float | None = None,
                exercise_minutes_today: float = 0, today: date | None = None) -> dict[str, Any]:
        current_day = today or date.today()
        days: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "hydration_ml": 0.0, "energy_kcal": 0.0, "protein_g": 0.0,
            "carbohydrate_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0,
            "sodium_mg": 0.0, "record_count": 0, "sources": set(),
        })
        for record in records:
            if not isinstance(record, dict) or record.get("type") not in {"hydration", "nutrition"}:
                continue
            stamp = str(record.get("start_time") or record.get("time") or "")[:10]
            try:
                date.fromisoformat(stamp)
            except ValueError:
                continue
            day = days[stamp]
            day["record_count"] += 1
            day["sources"].add(str(record.get("source") or record.get("source_device") or "unknown"))
            day["hydration_ml"] += _number(record.get("volume_ml")) or 0
            for target, source in (("energy_kcal", "energy_kcal"), ("protein_g", "protein_g"),
                                   ("carbohydrate_g", "carbohydrate_g"), ("fat_g", "fat_g"),
                                   ("fiber_g", "fiber_g"), ("sodium_mg", "sodium_mg")):
                day[target] += _number(record.get(source)) or 0

        history = []
        for stamp in sorted(days):
            item = dict(days[stamp])
            item["day"] = stamp
            item["sources"] = sorted(item["sources"])
            for key, value in list(item.items()):
                if isinstance(value, float):
                    item[key] = round(value, 1)
            history.append(item)
        today_item = next((item for item in history if item["day"] == current_day.isoformat()), None)
        if today_item is None:
            today_item = {"day": current_day.isoformat(), "hydration_ml": 0, "energy_kcal": 0,
                          "protein_g": 0, "carbohydrate_g": 0, "fat_g": 0, "fiber_g": 0,
                          "sodium_mg": 0, "record_count": 0, "sources": []}

        weight = _number(weight_kg)
        hydration_target = round(weight * 35 + max(0, exercise_minutes_today) / 60 * 500) if weight else None
        protein_target = round(weight * 1.6) if weight else None
        carbohydrate_target = round(weight * (4 if exercise_minutes_today >= 60 else 3)) if weight else None
        hydration_progress = (round(today_item["hydration_ml"] / hydration_target * 100)
                              if hydration_target else None)
        recommendations = []
        if today_item["record_count"] == 0:
            recommendations.append("Aucun apport enregistré aujourd’hui : Atlas ne conclut pas à un déficit.")
        elif hydration_progress is not None and hydration_progress < 60:
            recommendations.append("Hydratation enregistrée encore éloignée de votre repère quotidien.")
        if exercise_minutes_today >= 60 and today_item["carbohydrate_g"] > 0:
            recommendations.append("Séance longue détectée : Atlas surveille particulièrement les glucides et l’hydratation.")
        return {
            "today": today_item,
            "targets": {"hydration_ml": hydration_target, "protein_g": protein_target,
                        "carbohydrate_g": carbohydrate_target},
            "progress": {"hydration_percent": hydration_progress},
            "history": history[-90:],
            "recommendations": recommendations,
            "confidence": min(100, today_item["record_count"] * 20),
            "medical_notice": "Repères sportifs indicatifs, sans valeur de prescription médicale.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
