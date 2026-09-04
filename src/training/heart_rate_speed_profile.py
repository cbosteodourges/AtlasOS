"""Profil hebdomadaire allure–fréquence cardiaque à partir des blocs FIT.

Le modèle compare la charge interne à charge externe équivalente. Il ne modifie
jamais une référence sur une séance isolée et expose ses preuves au lieu de
transformer la conformité à une prescription en capacité physiologique.
"""

from collections import defaultdict
from datetime import date, timedelta


DOMAIN_TOKENS = {
    "endurance": ("z1", "z2", "endurance", "easy", "warmup", "échauff"),
    "tempo": ("z3", "tempo", "steady", "sub_threshold", "sous_seuil"),
    "threshold": ("sv2", "threshold", "seuil"),
    "vo2": ("vma", "vo2", "vo₂", "max_aerobic"),
}
MINIMUM_DURATION = {"endurance": 180, "tempo": 180, "threshold": 120, "vo2": 45}


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _weighted_mean(items, value_key):
    total_weight = sum(item["weight"] for item in items)
    if not total_weight:
        return None
    return sum(item[value_key] * item["weight"] for item in items) / total_weight


def _domain(block_type):
    value = str(block_type or "").lower().replace("-", "_").replace(" ", "_")
    for key, tokens in DOMAIN_TOKENS.items():
        if any(token in value for token in tokens):
            return key
    return None


def extract_comparable_blocks(executions, physiology):
    """Extrait les blocs stables possédant vitesse, FC, durée et date."""
    maximum_hr = _number(physiology.get("maximum_heart_rate_bpm")) or 220
    resting_hr = _number(physiology.get("resting_heart_rate_bpm"))
    blocks = []
    for session_index, item in enumerate(executions):
        activity = item.get("activity") or {}
        if activity.get("sport") not in {"running", "run", "road_running", "trail"}:
            continue
        try:
            session_date = date.fromisoformat(str(item.get("start_time") or "")[:10])
        except ValueError:
            continue
        analysis = item.get("analysis") or {}
        integrity = analysis.get("data_integrity") or {}
        if integrity.get("heart_rate_reliable") is False:
            continue
        quality = _number(activity.get("data_quality_score"))
        quality = max(25.0, min(100.0, quality if quality is not None else 60.0))
        temperature = _number(activity.get("temperature_c"))
        for block_index, block in enumerate(analysis.get("blocks") or []):
            raw_block_type = str(
                block.get("block_type") or block.get("type") or ""
            ).lower().replace("-", "_").replace(" ", "_")
            domain = _domain(raw_block_type)
            speed = _number(block.get("average_speed_kmh"))
            heart_rate = _number(block.get("average_heart_rate_bpm"))
            duration = _number(block.get("duration_seconds"))
            if not domain or not speed or not heart_rate or not duration:
                continue
            if speed < 6 or duration < MINIMUM_DURATION[domain]:
                continue
            if heart_rate < 70 or heart_rate > maximum_hr + 5:
                continue
            # Les températures extrêmes restent utilisables, mais pèsent moins.
            context_weight = 0.75 if temperature is not None and (temperature < 2 or temperature > 24) else 1.0
            hrr = None
            if resting_hr is not None and maximum_hr > resting_hr:
                hrr = (heart_rate - resting_hr) / (maximum_hr - resting_hr)
            blocks.append({
                "domain": domain,
                "raw_block_type": raw_block_type,
                "date": session_date,
                "session_id": str(item.get("activity_id") or f"{session_date}:{session_index}"),
                "block_id": block_index,
                "speed_kmh": speed,
                "speed_bin": round(speed / 0.2) * 0.2,
                "heart_rate_bpm": heart_rate,
                "heart_rate_reserve_ratio": hrr,
                "duration_seconds": duration,
                "temperature_c": temperature,
                "weight": (quality / 100.0) * context_weight * min(1.5, duration / 300.0),
            })
    return blocks


def _flat_physiology(physiology):
    """Accepte le format API plat et le profil interne imbriqué."""
    sv1 = physiology.get("sv1") or {}
    sv2 = physiology.get("sv2") or {}
    return {
        **physiology,
        "sv1_speed_kmh": physiology.get("sv1_speed_kmh", sv1.get("speed_kmh")),
        "sv1_heart_rate_bpm": physiology.get(
            "sv1_heart_rate_bpm", sv1.get("heart_rate_bpm")
        ),
        "sv2_speed_kmh": physiology.get("sv2_speed_kmh", sv2.get("speed_kmh")),
        "sv2_heart_rate_bpm": physiology.get(
            "sv2_heart_rate_bpm", sv2.get("heart_rate_bpm")
        ),
    }


def weekly_heart_rate_speed_profile(executions, physiology, as_of=None):
    """Compare 42 jours récents aux 140 jours précédents, allure par allure."""
    physiology = _flat_physiology(physiology)
    as_of = as_of or date.today()
    recent_start = as_of - timedelta(days=41)
    history_start = as_of - timedelta(days=181)
    blocks = extract_comparable_blocks(executions, physiology)
    model_blocks = [block for block in blocks if history_start <= block["date"] <= as_of]
    total_model_weight = sum(block["weight"] for block in model_blocks)
    personal_slope = None
    if len(model_blocks) >= 8 and total_model_weight:
        mean_speed = sum(block["speed_kmh"] * block["weight"] for block in model_blocks) / total_model_weight
        mean_hr = sum(block["heart_rate_bpm"] * block["weight"] for block in model_blocks) / total_model_weight
        covariance = sum(
            block["weight"] * (block["speed_kmh"] - mean_speed) * (block["heart_rate_bpm"] - mean_hr)
            for block in model_blocks
        )
        variance = sum(block["weight"] * (block["speed_kmh"] - mean_speed) ** 2 for block in model_blocks)
        fitted_slope = covariance / variance if variance else None
        if fitted_slope is not None and 4 <= fitted_slope <= 16:
            personal_slope = fitted_slope
    bpm_per_kmh = personal_slope or 8.0
    grouped = defaultdict(lambda: {"recent": [], "baseline": []})
    for block in blocks:
        if recent_start <= block["date"] <= as_of:
            grouped[(block["domain"], block["speed_bin"])]["recent"].append(block)
        elif history_start <= block["date"] < recent_start:
            grouped[(block["domain"], block["speed_bin"])]["baseline"].append(block)

    references = {
        "endurance": (_number(physiology.get("sv1_speed_kmh")), _number(physiology.get("sv1_heart_rate_bpm")), "SV1"),
        "tempo": (None, None, "Tempo"),
        "threshold": (_number(physiology.get("sv2_speed_kmh")), _number(physiology.get("sv2_heart_rate_bpm")), "SV2"),
        "vo2": (_number(physiology.get("vma_kmh")), _number(physiology.get("maximum_heart_rate_bpm")), "VMA"),
    }
    results = {}
    for domain in DOMAIN_TOKENS:
        comparisons = []
        for (group_domain, speed_bin), periods in grouped.items():
            if group_domain != domain:
                continue
            recent_sessions = {item["session_id"] for item in periods["recent"]}
            baseline_sessions = {item["session_id"] for item in periods["baseline"]}
            if len(periods["recent"]) < 2 or len(periods["baseline"]) < 2:
                continue
            if len(recent_sessions) < 2 or len(baseline_sessions) < 2:
                continue
            recent_hr = _weighted_mean(periods["recent"], "heart_rate_bpm")
            baseline_hr = _weighted_mean(periods["baseline"], "heart_rate_bpm")
            weight = min(len(periods["recent"]), len(periods["baseline"]))
            comparisons.append({
                "speed_kmh": speed_bin,
                "heart_rate_delta_bpm": recent_hr - baseline_hr,
                "recent_blocks": len(periods["recent"]),
                "baseline_blocks": len(periods["baseline"]),
                "recent_sessions": len(recent_sessions),
                "baseline_sessions": len(baseline_sessions),
                "weight": weight,
            })

        total_weight = sum(item["weight"] for item in comparisons)
        delta = (
            sum(item["heart_rate_delta_bpm"] * item["weight"] for item in comparisons) / total_weight
            if total_weight else None
        )
        recent_blocks = sum(item["recent_blocks"] for item in comparisons)
        baseline_blocks = sum(item["baseline_blocks"] for item in comparisons)
        recent_sessions = max((item["recent_sessions"] for item in comparisons), default=0)
        baseline_sessions = max((item["baseline_sessions"] for item in comparisons), default=0)
        enough = total_weight >= 3 and recent_sessions >= 2 and baseline_sessions >= 2
        trend = None
        if enough and delta is not None:
            trend = "en progression" if delta <= -2.5 else ("en retrait" if delta >= 2.5 else "stable")
        confidence = 0
        if comparisons:
            confidence = round(min(
                92,
                15
                + min(25, total_weight * 4)
                + min(20, recent_sessions * 5)
                + min(15, baseline_sessions * 3)
                + min(10, len(comparisons) * 5),
            ))
        recent_dates = [
            block["date"]
            for block in blocks
            if block["domain"] == domain and recent_start <= block["date"] <= as_of
        ]
        reference_speed, reference_hr, reference_name = references[domain]
        # La pente allure–FC personnelle convertit le changement cardiaque en
        # vitesse équivalente. Le déplacement hebdomadaire reste plafonné.
        speed_shift = max(-0.4, min(0.4, -delta / bpm_per_kmh)) if enough and delta is not None else None
        projected_speed = reference_speed + speed_shift if reference_speed is not None and speed_shift is not None else None
        results[domain] = {
            "heart_rate_delta_bpm": round(delta, 1) if delta is not None else None,
            "trend": trend,
            "confidence": confidence,
            "matched_speed_count": len(comparisons),
            "matched_speeds_kmh": sorted(round(item["speed_kmh"], 1) for item in comparisons),
            "recent_block_count": recent_blocks,
            "baseline_block_count": baseline_blocks,
            "recent_session_count": recent_sessions,
            "baseline_session_count": baseline_sessions,
            "latest_recent_date": max(recent_dates).isoformat() if recent_dates else None,
            "reference_name": reference_name,
            "reference_speed_kmh": reference_speed,
            "reference_heart_rate_bpm": reference_hr,
            "projected_speed_kmh": round(projected_speed, 2) if projected_speed is not None else None,
            "projected_speed_change_kmh": round(speed_shift, 2) if speed_shift is not None else None,
            "heart_rate_slope_bpm_per_kmh": round(bpm_per_kmh, 2),
            "heart_rate_slope_source": "personnelle" if personal_slope is not None else "prudente par défaut",
            "interpretation": (
                f"À allure comparable, la FC récente varie de {delta:+.1f} bpm."
                if enough and delta is not None else
                "Pas encore assez de blocs comparables entre les 42 derniers jours et l’historique."
            ),
        }

    vo2 = _number(physiology.get("vo2_max"))
    vma = _number(physiology.get("vma_kmh"))
    vo2_shift = results["vo2"].get("projected_speed_change_kmh")
    projected_vo2 = None
    if vo2_shift is not None:
        projected_vo2 = (vo2 + 3.33 * vo2_shift) if vo2 is not None else (3.5 + 3.33 * (vma + vo2_shift))
    return {
        "as_of": as_of.isoformat(),
        "week": f"{as_of.isocalendar().year}-S{as_of.isocalendar().week:02d}",
        "next_review": (as_of + timedelta(days=7 - as_of.weekday())).isoformat(),
        "recent_window_days": 42,
        "baseline_window_days": 140,
        "method": "Fréquence cardiaque à allure comparable, blocs FIT de plusieurs séances.",
        "domains": results,
        "projected_vo2_max": round(projected_vo2, 1) if projected_vo2 is not None else None,
        "guardrails": [
            "Aucune référence modifiée sur une séance isolée.",
            "Projection hebdomadaire plafonnée à ±0,4 km/h.",
            "VMA et VO₂max restent à confirmer par des efforts spécifiques ou une compétition.",
        ],
    }


def weekly_threshold_state_profile(executions, physiology, as_of=None):
    """Projette SV1 et SV2 comme couples vitesse–FC, sans les valider.

    La vitesse projetée provient de l'évolution de FC à allure comparable.
    La FC projetée ne provient que de blocs explicitement identifiés comme un
    travail de seuil proche de la référence. Elle n'est donc jamais déduite
    automatiquement d'une simple baisse de FC en endurance.
    """

    physiology = _flat_physiology(physiology)
    as_of = as_of or date.today()
    efficiency = weekly_heart_rate_speed_profile(
        executions, physiology, as_of=as_of
    )
    recent_start = as_of - timedelta(days=41)
    blocks = extract_comparable_blocks(executions, physiology)
    maximum_hr = _number(physiology.get("maximum_heart_rate_bpm"))
    resting_hr = _number(physiology.get("resting_heart_rate_bpm"))
    definitions = {
        "sv1": {
            "domain": "endurance",
            "speed": _number(physiology.get("sv1_speed_kmh")),
            "heart_rate": _number(physiology.get("sv1_heart_rate_bpm")),
            "tokens": ("sv1", "aerobic_threshold", "seuil_aerobie"),
        },
        "sv2": {
            "domain": "threshold",
            "speed": _number(physiology.get("sv2_speed_kmh")),
            "heart_rate": _number(physiology.get("sv2_heart_rate_bpm")),
            "tokens": ("sv2", "threshold", "seuil"),
        },
    }
    states = {}
    for name, definition in definitions.items():
        current_speed = definition["speed"]
        current_hr = definition["heart_rate"]
        domain_result = (efficiency.get("domains") or {}).get(
            definition["domain"], {}
        )
        projected_speed = _number(domain_result.get("projected_speed_kmh"))
        explicit = [
            block for block in blocks
            if recent_start <= block["date"] <= as_of
            and any(
                token in block.get("raw_block_type", "")
                for token in definition["tokens"]
            )
            and (
                current_speed is None
                or abs(block["speed_kmh"] - current_speed)
                <= max(.45, current_speed * .06)
            )
        ]
        sessions = {block["session_id"] for block in explicit}
        observed_hr = _weighted_mean(explicit, "heart_rate_bpm") if explicit else None
        projected_hr = current_hr
        if current_hr is not None and observed_hr is not None and len(sessions) >= 2:
            projected_hr = max(current_hr - 2, min(current_hr + 2, observed_hr))
        elif current_hr is None and observed_hr is not None and len(sessions) >= 2:
            projected_hr = observed_hr

        speed_delta = (
            projected_speed - current_speed
            if projected_speed is not None and current_speed is not None else None
        )
        hr_delta = (
            projected_hr - current_hr
            if projected_hr is not None and current_hr is not None else None
        )
        displayed_projected_hr = (
            round(projected_hr) if projected_hr is not None else None
        )
        confidence = min(
            int(domain_result.get("confidence") or 0),
            45 + min(30, len(sessions) * 10) + min(15, len(explicit) * 3),
        )
        usable = (
            current_speed is not None
            and current_hr is not None
            and projected_speed is not None
            and confidence >= 55
        )
        direction = None
        if usable and speed_delta is not None:
            direction = (
                "progression" if speed_delta >= .08
                else "regression" if speed_delta <= -.08
                else "stable"
            )
        states[name] = {
            "current": {
                "speed_kmh": current_speed,
                "heart_rate_bpm": current_hr,
                "heart_rate_percent_max": (
                    round(current_hr / maximum_hr * 100, 1)
                    if current_hr is not None and maximum_hr else None
                ),
            },
            "projection": {
                "speed_kmh": round(projected_speed, 2) if projected_speed is not None else None,
                "heart_rate_bpm": displayed_projected_hr,
                "heart_rate_percent_max": (
                    round(displayed_projected_hr / maximum_hr * 100, 1)
                    if displayed_projected_hr is not None and maximum_hr else None
                ),
                "heart_rate_reserve_percent": (
                    round((displayed_projected_hr - resting_hr) / (maximum_hr - resting_hr) * 100, 1)
                    if displayed_projected_hr is not None and resting_hr is not None
                    and maximum_hr and maximum_hr > resting_hr else None
                ),
            },
            "speed_change_kmh": round(speed_delta, 2) if speed_delta is not None else None,
            "heart_rate_change_bpm": round(hr_delta) if hr_delta is not None else None,
            "direction": direction,
            "confidence": confidence,
            "usable": usable,
            "threshold_specific_sessions": len(sessions),
            "threshold_specific_blocks": len(explicit),
            "status": "projection_a_confirmer" if usable else "donnees_insuffisantes",
            "explanation": (
                "Vitesse projetée par la relation allure–FC ; FC du seuil "
                "estimée uniquement à partir de blocs explicitement proches du seuil."
            ),
        }
    return {
        "schema": "threshold_state_v2",
        "week": efficiency["week"],
        "as_of": efficiency["as_of"],
        "next_review": efficiency["next_review"],
        "states": states,
        "validation_rule": (
            "Deux semaines consécutives concordantes sont nécessaires avant "
            "la modification automatique des références et du programme."
        ),
    }
