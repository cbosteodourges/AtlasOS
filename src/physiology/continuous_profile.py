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


def _timestamp(value: Any) -> float | None:
    if hasattr(value, "timestamp"):
        return float(value.timestamp())
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            ).timestamp()
        except (TypeError, ValueError):
            return None


def _bounded(previous: float | None, estimate: float, daily_change: float) -> float:
    if previous is None:
        return estimate
    return max(previous - daily_change, min(previous + daily_change, estimate))


def _best_sustained_speed(
    samples: Iterable[Any],
    minimum_seconds: float = 170,
    maximum_seconds: float = 210,
) -> float | None:
    """Meilleure médiane soutenue sur une durée, quelle que soit la fréquence."""

    points = sorted(
        (
            (stamp, speed * 3.6)
            for sample in samples
            if (stamp := _timestamp(getattr(sample, "timestamp", None))) is not None
            and (speed := _number(getattr(sample, "speed_mps", None))) is not None
            and 4 <= speed * 3.6 <= 30
        ),
        key=lambda item: item[0],
    )
    if len(points) < 12:
        return None

    candidates: list[float] = []
    for start_index, (start, _) in enumerate(points):
        window: list[float] = []
        previous_stamp = start
        for stamp, speed in points[start_index:]:
            if stamp - previous_stamp > 30 or stamp - start > maximum_seconds:
                break
            window.append(speed)
            previous_stamp = stamp
            if stamp - start >= minimum_seconds and len(window) >= 6:
                candidates.append(median(window))
                break
    return max(candidates) if candidates else None


class ContinuousPhysiologyEstimator:
    """Estime des tendances ; ne remplace pas une mesure de laboratoire."""

    def estimate(
        self,
        activities: Iterable[Any],
        current: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = current or {}
        declared_maximum_hr = _number(current.get("maximum_heart_rate_bpm"))
        usable_hr_ceiling = declared_maximum_hr or 220
        runs = [
            item for item in activities
            if str(getattr(item, "activity_type", "")).lower()
            in {"run", "running", "trail_running", "56"}
        ]
        sustained_speeds: list[float] = []
        recent_session_signals: list[dict[str, float]] = []
        threshold_speeds: list[float] = []
        threshold_hr: list[float] = []

        for activity in runs:
            samples = getattr(activity, "samples", []) or []
            sustained = _best_sustained_speed(samples)
            if sustained is not None:
                sustained_speeds.append(sustained)
            short_sustained = _best_sustained_speed(samples, 80, 110)
            if sustained is not None and short_sustained is not None:
                activity_stamp = _timestamp(getattr(activity, "start_time", None))
                recent_session_signals.append({
                    "three_minutes_kmh": sustained,
                    "ninety_seconds_kmh": short_sustained,
                    "activity_timestamp": activity_stamp or 0.0,
                })

            average = _number(getattr(activity, "average_speed_mps", None))
            duration_seconds = _number(getattr(activity, "duration_seconds", None))
            duration_minutes = _number(getattr(activity, "duration_minutes", None))
            duration = duration_seconds or ((duration_minutes or 0) * 60)
            heart_rate = _number(getattr(activity, "average_heart_rate_bpm", None))
            sample_speeds = [
                value * 3.6
                for sample in samples
                if (value := _number(getattr(sample, "speed_mps", None))) is not None
            ]
            variable_session = (
                len(sample_speeds) >= 12
                and max(sample_speeds) - min(sample_speeds) > 3.0
            )
            if (
                average
                and duration >= 900
                and heart_rate
                and 145 <= heart_rate <= usable_hr_ceiling
                and not variable_session
            ):
                threshold_speeds.append(average * 3.6)
                threshold_hr.append(heart_rate)

        quality_evidence = len(sustained_speeds) * 2 + len(threshold_speeds)
        confidence = min(
            .90,
            .25 + min(len(runs), 20) * .01 + quality_evidence * .06,
        )
        if not runs or confidence < .32:
            return {
                "updated": False,
                "confidence": round(confidence, 2),
                "evidence_sessions": len(runs),
                "quality_evidence_count": quality_evidence,
                "reason": "Historique de course encore insuffisant.",
            }

        observed_vma = (
            max(sustained_speeds)
            if sustained_speeds
            else max(threshold_speeds, default=0) * 1.10
        )
        if not observed_vma:
            return {
                "updated": False,
                "confidence": round(confidence, 2),
                "evidence_sessions": len(runs),
                "quality_evidence_count": quality_evidence,
                "reason": "Aucune fenêtre temporelle exploitable.",
            }

        observed_vma = max(7, min(25, observed_vma))
        observed_sv2 = (
            median(sorted(threshold_speeds)[-5:])
            if threshold_speeds else observed_vma * .88
        )
        observed_sv2 = max(
            observed_vma * .78,
            min(observed_vma * .94, observed_sv2),
        )
        observed_sv1 = observed_sv2 * .82

        old_vma = _number(
            current.get("vma_kmh") or current.get("vma_training_reference_kmh")
        )
        old_vo2 = _number(current.get("vo2_max"))
        sv1_current = current.get("sv1") or {}
        sv2_current = current.get("sv2") or {}
        old_sv1 = _number(sv1_current.get("speed_kmh"))
        old_sv2 = _number(sv2_current.get("speed_kmh"))

        # Réactivité courte : une séance de qualité peut confirmer immédiatement
        # un gain modeste de VO2max. Il faut à la fois soutenir près de la VMA
        # pendant trois minutes et dépasser cette référence sur une fraction
        # courte. Ce signal ne déplace pas, à lui seul, les seuils ventilatoires.
        fast_vo2_signal = False
        strongest_signal: dict[str, float] | None = None
        if old_vma is not None and recent_session_signals:
            # La réaction immédiate concerne la dernière séance exploitable,
            # pas le meilleur effort éventuellement ancien de tout l'historique.
            strongest_signal = max(
                recent_session_signals,
                key=lambda item: item["activity_timestamp"],
            )
            fast_vo2_signal = (
                strongest_signal["three_minutes_kmh"] >= old_vma * .97
                and strongest_signal["ninety_seconds_kmh"] >= old_vma * 1.03
                and (
                    old_vo2 is None
                    or strongest_signal["ninety_seconds_kmh"] * 3.5
                    >= old_vo2 + .5
                )
            )

        proposed_vma = _bounded(old_vma, observed_vma, .2)
        proposed_vo2 = _bounded(old_vo2, 3.5 * proposed_vma, .7)
        if fast_vo2_signal and old_vo2 is not None:
            session_vo2 = round(strongest_signal["ninety_seconds_kmh"] * 3.5)
            next_integer = round(old_vo2) + 1
            proposed_vo2 = max(
                proposed_vo2,
                min(float(next_integer), float(session_vo2)),
            )
        proposed_sv1 = (
            _bounded(old_sv1, observed_sv1, .15)
            if threshold_speeds else (old_sv1 or observed_sv1)
        )
        proposed_sv2 = (
            _bounded(old_sv2, observed_sv2, .15)
            if threshold_speeds else (old_sv2 or observed_sv2)
        )

        # Une absence de test maximal n'est pas une preuve de régression.
        vma = round(max(old_vma or proposed_vma, proposed_vma), 2)
        vo2 = round(max(old_vo2 or proposed_vo2, proposed_vo2), 1)
        sv1 = round(max(old_sv1 or proposed_sv1, proposed_sv1), 2)
        sv2 = round(max(old_sv2 or proposed_sv2, proposed_sv2), 2)

        sv2_hr = sv2_current.get("heart_rate_bpm")
        if threshold_hr and sv2_hr is None:
            sv2_hr = round(median(threshold_hr))
        maximum_hr = declared_maximum_hr
        sv1_hr = sv1_current.get("heart_rate_bpm")
        if sv1_hr is None and maximum_hr:
            sv1_hr = round(maximum_hr * .81)

        improvements = []
        if old_vma is not None and vma > old_vma:
            improvements.append("vma")
        if old_vo2 is not None and vo2 > old_vo2:
            improvements.append("vo2_max")

        return {
            "updated": True,
            "confidence": round(confidence, 2),
            "evidence_sessions": len(runs),
            "quality_evidence_count": quality_evidence,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "method": "fenêtres temporelles et références validées protégées",
            "decision": "increase_candidate" if improvements else "maintain_reference",
            "improvements": improvements,
            "vo2_max": vo2,
            "vma_kmh": vma,
            "vma_training_reference_kmh": vma,
            "sv1": {
                "speed_kmh": sv1,
                "heart_rate_bpm": sv1_hr,
                "status": "longitudinal_estimate",
            },
            "sv2": {
                "speed_kmh": sv2,
                "heart_rate_bpm": sv2_hr,
                "status": "longitudinal_estimate",
            },
            "observed": {
                "vma_kmh": round(observed_vma, 2),
                "sv2_speed_kmh": round(observed_sv2, 2),
                "fast_vo2_signal": fast_vo2_signal,
                "strongest_session": (
                    {
                        key: round(value, 2)
                        for key, value in strongest_signal.items()
                        if key != "activity_timestamp"
                    }
                    if strongest_signal else None
                ),
            },
            "maximum_heart_rate_bpm": maximum_hr,
            "warning": (
                "Estimation d’entraînement, non mesure médicale. "
                "Une observation inférieure ne réduit jamais automatiquement "
                "une référence physiologique validée."
            ),
        }
