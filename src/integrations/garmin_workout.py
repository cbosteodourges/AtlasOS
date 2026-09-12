"""Conversion des séances Atlas vers le format d'entraînement Garmin FIT."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from garmin_fit_sdk import Encoder


SPORTS = {"running": "running", "cycling": "cycling"}
INTENSITIES = {
    "warm_up": "warmup",
    "work": "interval",
    "continuous": "active",
    "recovery": "recovery",
    "cool_down": "cooldown",
}
ROLE_ALIASES = {
    "warmup": "warm_up",
    "interval": "work",
    "cooldown": "cool_down",
}


def _fit_text(value: Any, maximum_bytes: int = 240) -> str:
    """Limite un texte UTF-8 sans couper un caractère multioctet."""
    encoded = str(value or "").encode("utf-8")[:maximum_bytes]
    return encoded.decode("utf-8", errors="ignore")


def _pace_seconds(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value) * 60
    match = re.fullmatch(r"\s*(\d+)(?::|['’])(\d{1,2})(?:[\"”])?\s*", str(value))
    if not match:
        raise ValueError(f"Allure Atlas invalide : {value}")
    return int(match.group(1)) * 60 + int(match.group(2))


def _speed_range(target: dict[str, Any]) -> tuple[float, float] | None:
    minimum = target.get("speed_min_kmh")
    maximum = target.get("speed_max_kmh")
    if minimum is not None and maximum is not None:
        values = sorted((float(minimum) / 3.6, float(maximum) / 3.6))
        return values[0], values[1]

    # Une allure rapide correspond à une vitesse haute, et inversement.
    fast = _pace_seconds(target.get("pace_min_per_km"))
    slow = _pace_seconds(target.get("pace_max_per_km"))
    if fast and slow:
        values = sorted((1000 / slow, 1000 / fast))
        return values[0], values[1]
    return None


def _target_fields(target: dict[str, Any]) -> dict[str, Any]:
    speeds = _speed_range(target)
    if speeds:
        return {
            "target_type": "speed",
            "target_value": 0,
            # Le champ conteneur FIT stocke la vitesse en millièmes de m/s.
            "custom_target_value_low": round(speeds[0] * 1000),
            "custom_target_value_high": round(speeds[1] * 1000),
        }

    low = target.get("heart_rate_min_bpm")
    high = target.get("heart_rate_max_bpm")
    if low is not None and high is not None:
        # FIT distingue les bpm des pourcentages en ajoutant 100 aux bpm.
        return {
            "target_type": "heart_rate",
            "target_value": 0,
            "custom_target_value_low": int(low) + 100,
            "custom_target_value_high": int(high) + 100,
        }

    return {"target_type": "open", "target_value": 0}


def universal_workout(workout: dict[str, Any]) -> dict[str, Any]:
    """Produit la représentation stable utilisée par tous les connecteurs."""
    sport = str(workout.get("sport") or "running").lower()
    if sport not in SPORTS:
        raise ValueError("L'export montre prend actuellement en charge la course et le vélo.")

    steps: list[dict[str, Any]] = []
    for block in workout.get("blocks") or []:
        repetitions = max(1, int(block.get("repetitions") or 1))
        recovery = (
            float(block["recovery_minutes"]) * 60
            if block.get("recovery_minutes") is not None
            else float(block.get("recovery_seconds") or 0)
        )
        role = str(block.get("block_type") or "continuous").lower().replace("-", "_")
        role = ROLE_ALIASES.get(role, role)
        for repetition in range(repetitions):
            step = {
                "name": _fit_text(block.get("name") or "Étape", 120),
                "role": role,
                "target": dict(block.get("target") or {}),
                "instructions": _fit_text(block.get("instructions") or "", 220),
            }
            if block.get("distance_meters") is not None:
                step.update(duration_type="distance", duration_value=float(block["distance_meters"]))
            elif block.get("duration_minutes") is not None:
                step.update(duration_type="time", duration_value=float(block["duration_minutes"]) * 60)
            elif block.get("duration_seconds") is not None:
                step.update(duration_type="time", duration_value=float(block["duration_seconds"]))
            else:
                raise ValueError(f"Le bloc « {step['name']} » n'a ni durée ni distance.")
            steps.append(step)
            if recovery > 0 and repetition < repetitions - 1:
                steps.append({
                    "name": "Récupération",
                    "role": "recovery",
                    "duration_type": "time",
                    "duration_value": recovery,
                    "target": {},
                    "instructions": "Récupération active",
                })

    if not steps:
        raise ValueError("La séance ne contient aucune étape exportable.")
    return {
        "schema": "atlas.workout.v1",
        "workout_id": str(workout.get("workout_id") or ""),
        "date": str(workout.get("workout_date") or "")[:10],
        "name": _fit_text(workout.get("title") or "Séance Atlas", 180),
        "description": _fit_text(workout.get("objective") or "", 220),
        "sport": sport,
        "steps": steps,
    }


def encode_garmin_fit(workout: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Encode une séance Atlas dans un fichier FIT chargeable sur une Garmin."""
    normalized = universal_workout(workout)
    encoder = Encoder()
    encoder.write_mesg({
        "mesg_num": 0,
        "type": "workout",
        "manufacturer": "development",
        "product": 0,
        "serial_number": 0,
        "time_created": datetime.now(timezone.utc),
        "product_name": "Atlas OS",
    })
    encoder.write_mesg({
        "mesg_num": 26,
        "sport": SPORTS[normalized["sport"]],
        "capabilities": 1 | 2 | 128 | 256 | 512,
        "num_valid_steps": len(normalized["steps"]),
        "wkt_name": normalized["name"],
        "wkt_description": normalized["description"],
    })
    for index, step in enumerate(normalized["steps"]):
        duration_type = step["duration_type"]
        message = {
            "mesg_num": 27,
            "message_index": index,
            "wkt_step_name": step["name"],
            "duration_type": duration_type,
            # duration_value est un conteneur brut : ms pour le temps,
            # centimètres pour la distance.
            "duration_value": round(
                step["duration_value"] * (1000 if duration_type == "time" else 100)
            ),
            "intensity": INTENSITIES.get(step["role"], "active"),
            "notes": step.get("instructions") or step["name"],
            **_target_fields(step["target"]),
        }
        encoder.write_mesg(message)
    return encoder.close(), normalized


def safe_filename(workout: dict[str, Any]) -> str:
    source = f"{workout.get('workout_date', '')}-{workout.get('title', 'seance-atlas')}"
    slug = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-")
    return f"{slug[:72] or 'seance-atlas'}.fit"
