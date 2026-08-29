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
                exercise_minutes_today: float = 0, height_cm: float | None = None,
                age_years: int | None = None, biological_sex: str | None = None,
                activity_energy_kcal: float = 0, activity_count: int = 0,
                activity_calorie_count: int = 0,
                measured_total_energy_kcal: float | None = None,
                measured_active_energy_kcal: float | None = None,
                measured_basal_energy_kcal: float | None = None,
                today: date | None = None) -> dict[str, Any]:
        current_day = today or date.today()
        days: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "hydration_ml": 0.0, "energy_kcal": 0.0, "protein_g": 0.0,
            "carbohydrate_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0,
            "sodium_mg": 0.0, "sugar_g": 0.0, "calcium_mg": 0.0,
            "iron_mg": 0.0, "magnesium_mg": 0.0, "potassium_mg": 0.0,
            "zinc_mg": 0.0, "vitamin_c_mg": 0.0, "vitamin_d_mcg": 0.0,
            "vitamin_b12_mcg": 0.0, "caffeine_mg": 0.0,
            "record_count": 0, "sources": set(),
        })
        for record in records:
            if not isinstance(record, dict) or record.get("type") not in {"hydration", "nutrition"}:
                continue
            stamp = str(record.get("local_day") or record.get("start_time") or record.get("time") or "")[:10]
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
                                   ("fiber_g", "fiber_g"), ("sodium_mg", "sodium_mg"),
                                   ("sugar_g", "sugar_g"), ("calcium_mg", "calcium_mg"),
                                   ("iron_mg", "iron_mg"), ("magnesium_mg", "magnesium_mg"),
                                   ("potassium_mg", "potassium_mg"), ("zinc_mg", "zinc_mg"),
                                   ("vitamin_c_mg", "vitamin_c_mg"), ("vitamin_d_mcg", "vitamin_d_mcg"),
                                   ("vitamin_b12_mcg", "vitamin_b12_mcg"), ("caffeine_mg", "caffeine_mg")):
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
                          "sodium_mg": 0, "sugar_g": 0, "calcium_mg": 0, "iron_mg": 0,
                          "magnesium_mg": 0, "potassium_mg": 0, "zinc_mg": 0,
                          "vitamin_c_mg": 0, "vitamin_d_mcg": 0, "vitamin_b12_mcg": 0,
                          "caffeine_mg": 0, "record_count": 0, "sources": []}

        weight = _number(weight_kg)
        height = _number(height_cm)
        age = _number(age_years)
        sex = str(biological_sex or "").strip().lower()
        basal_energy = None
        if weight and height and age and sex:
            sex_adjustment = 5 if sex in {"male", "m", "homme", "masculin"} else -161
            basal_energy = round(10 * weight + 6.25 * height - 5 * age + sex_adjustment)
        estimated_basal = basal_energy
        measured_basal = _number(measured_basal_energy_kcal)
        basal_energy = round(max(0, measured_basal)) if measured_basal is not None else estimated_basal
        sport_energy = round(max(0, _number(activity_energy_kcal) or 0))
        measured_active = _number(measured_active_energy_kcal)
        active_energy = round(max(0, measured_active)) if measured_active is not None else None
        measured_total = _number(measured_total_energy_kcal)
        known_total = round(max(0, measured_total)) if measured_total is not None else (
            basal_energy + active_energy if basal_energy is not None and active_energy is not None else
            basal_energy + sport_energy if basal_energy is not None else
            sport_energy if activity_calorie_count else None
        )
        energy_expenditure = {
            "basal_kcal": basal_energy,
            "basal_source": "health_connect" if measured_basal is not None else "profile_estimate",
            "active_kcal": active_energy,
            "sport_kcal": sport_energy,
            "known_total_kcal": known_total,
            "total_source": "health_connect" if measured_total is not None else "atlas_partial",
            "activity_count": max(0, int(activity_count or 0)),
            "activity_calorie_count": max(0, int(activity_calorie_count or 0)),
            "sport_coverage_complete": bool(activity_count) and activity_count == activity_calorie_count,
            "scope": (
                "Dépense totale transmise par Santé Connect."
                if measured_total is not None else
                "Métabolisme basal + calories actives transmises."
                if active_energy is not None else
                "Métabolisme basal + activités sportives importées ; activité quotidienne et digestion non incluses."
            ),
        }
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
            "energy_expenditure": energy_expenditure,
            "education": [
                {"title": "Récupération", "tone": "positive",
                 "text": "Après l’effort, glucides, protéines, lipides et hydratation contribuent ensemble à restaurer les réserves et soutenir l’adaptation."},
                {"title": "Fibres et course", "tone": "watch",
                 "text": "Les fibres restent utiles au quotidien, mais peuvent être réduites avant une course si vous êtes sensible sur le plan digestif."},
                {"title": "Magnésium, fer et minéraux", "tone": "neutral",
                 "text": "Atlas privilégie les sources alimentaires variées. Une supplémentation ou une suspicion de carence doit être individualisée et, pour le fer, guidée par un bilan professionnel."},
            ],
            "history": history[-90:],
            "recommendations": recommendations,
            "confidence": min(100, today_item["record_count"] * 20),
            "medical_notice": "Repères sportifs indicatifs, sans valeur de prescription médicale.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
