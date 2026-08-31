"""Indice de récupération Atlas explicable, utilisable avec ou sans VFC."""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Iterable

from src.physiology.personal_indicator import PersonalIndicatorInterpreter


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
        # Une heure manquante est un déficit significatif, surtout lorsqu'Atlas
        # ne dispose pas encore des marqueurs physiologiques de la même nuit.
        return max(0, 100 - (target - hours) * 45)
    if hours <= target + 1:
        return 100
    return max(45, 100 - (hours - target - 1) * 10)


def _calibrate_partial_score(
    raw_score: float,
    duration_score: float,
    sleep_deficit_minutes: int,
    *,
    hrv_available: bool,
    nocturnal_hr_available: bool,
) -> int:
    """Empêche des données partielles favorables de produire un faux excellent."""
    calibrated = float(raw_score)
    if not hrv_available:
        calibrated = min(calibrated, 84)
        if sleep_deficit_minutes >= 30:
            calibrated = min(calibrated, duration_score + 5)
    if not hrv_available and not nocturnal_hr_available:
        calibrated = min(calibrated, 75)
    return round(max(0, min(100, calibrated)))


def _baseline(values: list[float], fallback: float | None = None) -> float | None:
    return mean(values[-28:]) if len(values) >= 3 else fallback


class AtlasRecoveryIndex:
    """Construit un score transparent sans fabriquer de VFC absente."""

    def build(
        self,
        wellness: Iterable[dict[str, Any]],
        activities: Iterable[Any],
        outcomes: Iterable[dict[str, Any]] = (),
    ) -> dict[str, Any]:
        records = [item for item in wellness if isinstance(item, dict)]
        sleeps = [item for item in records if item.get("type") == "sleep"]

        # Une sieste terminée le même jour ne doit jamais remplacer la nuit
        # principale dans l'indice de récupération. Atlas conserve, pour
        # chaque date, le sommeil ayant la plus longue durée réelle.
        primary_sleep_by_day: dict[str, tuple[float, dict[str, Any]]] = {}
        for sleep in sleeps:
            sleep_start = _dt(sleep.get("start_time"))
            sleep_end = _dt(sleep.get("end_time"))
            if not sleep_start or not sleep_end or sleep_end <= sleep_start:
                continue

            stage_totals: dict[str, float] = defaultdict(float)
            for stage in sleep.get("stages") or []:
                stage_start = _dt(stage.get("start_time"))
                stage_end = _dt(stage.get("end_time"))
                if stage_start and stage_end and stage_end > stage_start:
                    stage_totals[str(stage.get("stage"))] += (
                        stage_end - stage_start
                    ).total_seconds()

            explicit_sleep_seconds = sum(
                stage_totals.get(code, 0)
                for code in ("2", "4", "5", "6")
            )
            awake_seconds = sum(
                stage_totals.get(code, 0)
                for code in ("1", "3", "7")
            )
            session_seconds = (sleep_end - sleep_start).total_seconds()
            transmitted_seconds = _number(sleep.get("duration_seconds"))

            actual_sleep_seconds = (
                transmitted_seconds
                if transmitted_seconds is not None and transmitted_seconds > 0
                else explicit_sleep_seconds
                if explicit_sleep_seconds > 0
                else max(0, session_seconds - awake_seconds)
            )

            day = sleep_end.date().isoformat()
            current = primary_sleep_by_day.get(day)
            if current is None or actual_sleep_seconds > current[0]:
                primary_sleep_by_day[day] = (actual_sleep_seconds, sleep)

        sleeps = [
            selected[1]
            for day, selected in sorted(primary_sleep_by_day.items())
        ]
        resting = [item for item in records if item.get("type") == "resting_heart_rate"]
        hrv = [item for item in records if item.get("type") == "hrv_rmssd"]
        heart_series = [item for item in records if item.get("type") == "heart_rate_series"]
        by_day: dict[str, dict[str, Any]] = {}
        resting_values: list[float] = []
        hrv_values: list[float] = []
        sleep_duration_values: list[float] = []
        successful_sleep_values: list[float] = []
        night_hr_values: list[float] = []
        successful_night_hr_values: list[float] = []
        outcome_by_day: dict[str, float] = {}
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            stamp = _dt(outcome.get("start_time"))
            match = outcome.get("atlas_workout_match") or {}
            execution = match.get("execution") or {}
            execution_score = _number(
                execution.get("execution_score")
                or match.get("execution_score")
            )
            if stamp and execution_score is not None:
                outcome_by_day[stamp.date().isoformat()] = execution_score

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
            awake_seconds = sum(
                stages.get(code, 0)
                for code in ("1", "3", "7")
            )
            explicit_sleep_seconds = sum(
                stages.get(code, 0)
                for code in ("2", "4", "5", "6")
            )
            sleep_seconds = (
                explicit_sleep_seconds
                if explicit_sleep_seconds > 0
                else max(0, duration - awake_seconds)
            )
            if sleep_seconds <= 0:
                sleep_seconds = duration
            sleep_hours = sleep_seconds / 3600
            usual_sleep_target = _baseline(sleep_duration_values, 8.0) or 8.0
            performance_sleep_target = _baseline(successful_sleep_values)
            sleep_target = (
                performance_sleep_target
                if performance_sleep_target is not None
                else usual_sleep_target
            )
            sleep_target = max(7.5, min(9.0, sleep_target))
            components = [{"key": "sleep_duration", "label": "Durée du sommeil",
                           "score": _score_sleep_duration(sleep_hours, sleep_target),
                           "weight": 35, "value": round(sleep_hours, 2), "unit": "h",
                           "personal_target_hours": round(sleep_target, 2),
                           "difference_minutes": round((sleep_hours - sleep_target) * 60)}]
            known = sum(stages.values())
            if known:
                deep = stages.get("5", 0) / sleep_seconds
                rem = stages.get("6", 0) / sleep_seconds
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
            nocturnal = mean(sleep_hr) if sleep_hr else None
            night_hr_target = None
            if nocturnal is not None:
                usual_night_hr = _baseline(night_hr_values, nocturnal) or nocturnal
                performance_night_hr = _baseline(successful_night_hr_values)
                night_hr_target = (
                    performance_night_hr
                    if performance_night_hr is not None
                    else usual_night_hr
                )
                difference = nocturnal - night_hr_target
                components.append({
                    "key": "night_hr",
                    "label": "Fréquence cardiaque nocturne",
                    "score": max(20, min(100, 82 - difference * 7)),
                    "weight": 15,
                    "value": round(nocturnal, 1),
                    "personal_target": round(night_hr_target, 1),
                    "difference_bpm": round(difference, 1),
                    "unit": "bpm",
                })
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
            raw_score = round(
                sum(item["score"] * item["weight"] for item in components)
                / total_weight
            )
            sleep_deficit_minutes = max(
                0, round((sleep_target - sleep_hours) * 60)
            )
            duration_score = next(
                item["score"] for item in components
                if item["key"] == "sleep_duration"
            )
            score = _calibrate_partial_score(
                raw_score,
                duration_score,
                sleep_deficit_minutes,
                hrv_available=hrv_value is not None,
                nocturnal_hr_available=nocturnal is not None,
            )
            confidence = round(min(
                95 if hrv_value is not None else 75,
                25 + len(components) * 12
                + min(20, len(sleep_duration_values))
                + min(10, len(resting_values)),
            ))
            if sleep_deficit_minutes >= 15:
                guidance = (
                    f"Pour optimiser votre récupération, visez environ "
                    f"{int(sleep_target)} h "
                    f"{round((sleep_target % 1) * 60):02d}, soit environ "
                    f"{sleep_deficit_minutes} min de plus que cette nuit."
                )
            elif (
                nocturnal is not None
                and night_hr_target is not None
                and nocturnal <= night_hr_target + 1
            ):
                guidance = (
                    "Durée proche de votre besoin et fréquence cardiaque "
                    "nocturne favorable par rapport à votre référence."
                )
            else:
                guidance = (
                    "Durée proche de votre référence personnelle ; "
                    "confirmez avec votre ressenti et la réponse à la séance."
                )
            missing_data = []
            if hrv_value is None:
                missing_data.append("VFC nocturne")
            if nocturnal is None:
                missing_data.append("fréquence cardiaque nocturne")
            data_complete = not missing_data
            night_reference = (
                f" et FC nocturne cible {night_hr_target:.1f} bpm"
                if night_hr_target is not None else ""
            )
            if sleep_deficit_minutes:
                evolution = (
                    f"Sommeil inférieur de {sleep_deficit_minutes} min "
                    f"à la cible personnelle"
                )
            else:
                evolution = "Sommeil conforme à la cible personnelle"
            if (
                nocturnal is not None
                and night_hr_target is not None
            ):
                difference = nocturnal - night_hr_target
                evolution += (
                    f" ; FC nocturne {abs(difference):.1f} bpm "
                    f"{'au-dessus' if difference > 0 else 'sous'} la référence"
                )
            consequence = (
                "Conditions compatibles avec une bonne réponse à la séance, "
                "à confirmer par le ressenti."
                if score >= 70 else
                "Récupération susceptible de limiter la qualité de la séance."
            )
            interpretation = PersonalIndicatorInterpreter.interpret(
                indicator="recovery",
                current={
                    "atlas_index": score,
                    "sleep_hours": round(sleep_hours, 2),
                    "night_hr_bpm": (
                        round(nocturnal, 1)
                        if nocturnal is not None else None
                    ),
                },
                personal_reference=(
                    f"Sommeil cible {sleep_target:.2f} h"
                    f"{night_reference}"
                ),
                optimal_zone=(
                    "Zone apprise à partir des nuits suivies des meilleures séances."
                    if len(successful_sleep_values) >= 3 else
                    "Zone personnelle en construction à partir de l'historique."
                ),
                evolution=evolution,
                probable_consequence=consequence,
                recommendation=guidance,
                favorability_score=score,
                confidence=confidence,
                data_complete=data_complete,
                missing_data=missing_data,
            )
            by_day[day] = {
                "day": day,
                "atlas_recovery_index": score,
                "atlas_index": score,
                "raw_score_before_partial_calibration": raw_score,
                "confidence": confidence,
                "components": components,
                "hrv_used": hrv_value is not None,
                "personal_sleep_target_hours": round(sleep_target, 2),
                "sleep_deficit_minutes": sleep_deficit_minutes,
                "personal_night_hr_target_bpm": (
                    round(night_hr_target, 1)
                    if night_hr_target is not None else None
                ),
                "performance_learning_days": len(successful_sleep_values),
                "guidance": guidance,
                "interpretation": interpretation,
                "explanation": (
                    "Score fondé sur les mesures disponibles et vos références "
                    "personnelles ; les nuits suivies de bonnes séances "
                    "affinent progressivement les cibles."
                ),
            }
            sleep_duration_values.append(sleep_hours)
            if nocturnal is not None:
                night_hr_values.append(nocturnal)
            if outcome_by_day.get(day, 0) >= 80:
                successful_sleep_values.append(sleep_hours)
                if nocturnal is not None:
                    successful_night_hr_values.append(nocturnal)
            if resting_value is not None:
                resting_values.append(resting_value)
            if hrv_value is not None:
                hrv_values.append(hrv_value)
        history = [by_day[key] for key in sorted(by_day)]
        return {"latest": history[-1] if history else None, "history": history,
                "generated_at": datetime.now(timezone.utc).isoformat()}
