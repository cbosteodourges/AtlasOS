"""Moteur physiologique central d'ATLAS OS.

Ce module transforme des mesures quotidiennes simples en indicateurs lisibles
par Atlas Brain et par le futur tableau de bord. Il utilise uniquement la
bibliotheque standard Python et accepte les donnees manquantes.

Important : les resultats sont des aides au suivi et a la decision sportive.
Ils ne constituent ni un diagnostic medical ni une autorisation de pratiquer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


Number = Optional[float]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Limite une valeur entre minimum et maximum."""
    return max(minimum, min(maximum, value))


def _ratio_score(value: Number, baseline: Number, inverse: bool = False) -> Number:
    """Convertit l'ecart a une valeur habituelle en score sur 100."""
    if value is None or baseline in (None, 0):
        return None
    ratio = float(value) / float(baseline)
    if inverse:
        ratio = 2.0 - ratio
    return _clamp(50.0 + (ratio - 1.0) * 125.0)


def _weighted_average(items: list[tuple[Number, float]]) -> tuple[float, float]:
    """Renvoie la moyenne ponderee et la proportion de donnees disponibles."""
    available = [(float(value), weight) for value, weight in items if value is not None]
    total_possible = sum(weight for _, weight in items)
    total_available = sum(weight for _, weight in available)
    if not available or total_available == 0:
        return 50.0, 0.0
    score = sum(value * weight for value, weight in available) / total_available
    confidence = 100.0 * total_available / total_possible if total_possible else 0.0
    return _clamp(score), _clamp(confidence)


@dataclass(slots=True)
class PhysiologyInput:
    """Mesures du jour et valeurs habituelles personnelles.

    Tous les champs sont facultatifs. Les echelles de stress, fatigue et
    courbatures vont de 0 (aucun) a 10 (maximum).
    """

    hrv_ms: Number = None
    hrv_baseline_ms: Number = None
    resting_hr_bpm: Number = None
    resting_hr_baseline_bpm: Number = None
    sleep_hours: Number = None
    sleep_need_hours: float = 8.0
    sleep_quality_0_100: Number = None
    stress_0_10: Number = None
    subjective_fatigue_0_10: Number = None
    muscle_soreness_0_10: Number = None
    acute_load_7d: Number = None
    chronic_load_28d: Number = None
    vo2max: Number = None
    vo2max_baseline: Number = None
    pain_0_10: Number = None
    illness_symptoms: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PhysiologyInput":
        """Cree une entree depuis un dictionnaire ou un futur fichier JSON."""
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass(slots=True)
class PhysiologyResult:
    """Resultat standard transmis au tableau de bord et a Atlas Brain."""

    recovery_score: float
    fatigue_score: float
    readiness_score: float
    sleep_score: float
    autonomic_score: float
    load_score: float
    data_confidence: float
    status: str
    risk_level: str
    recommendation: str
    alerts: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Retourne un dictionnaire serialisable en JSON."""
        return asdict(self)


class PhysiologyEngine:
    """Analyse physiologique deterministe et explicable d'ATLAS OS."""

    VERSION = "0.6.0"

    def analyze(self, data: PhysiologyInput | dict[str, Any]) -> PhysiologyResult:
        """Analyse les mesures et produit la disponibilite du jour."""
        if isinstance(data, dict):
            data = PhysiologyInput.from_dict(data)
        self._validate(data)

        hrv_score = _ratio_score(data.hrv_ms, data.hrv_baseline_ms)
        resting_hr_score = _ratio_score(
            data.resting_hr_bpm, data.resting_hr_baseline_bpm, inverse=True
        )
        autonomic_score, autonomic_confidence = _weighted_average(
            [(hrv_score, 0.65), (resting_hr_score, 0.35)]
        )

        duration_score = None
        if data.sleep_hours is not None and data.sleep_need_hours > 0:
            duration_score = _clamp(100.0 * data.sleep_hours / data.sleep_need_hours)
        sleep_score, sleep_confidence = _weighted_average(
            [(duration_score, 0.60), (data.sleep_quality_0_100, 0.40)]
        )

        load_ratio = None
        if data.acute_load_7d is not None and data.chronic_load_28d not in (None, 0):
            load_ratio = data.acute_load_7d / data.chronic_load_28d
        load_score = self._load_score(load_ratio)
        load_confidence = 100.0 if load_ratio is not None else 0.0

        stress_score = None if data.stress_0_10 is None else 100.0 - data.stress_0_10 * 10.0
        fatigue_input_score = (
            None
            if data.subjective_fatigue_0_10 is None
            else 100.0 - data.subjective_fatigue_0_10 * 10.0
        )
        soreness_score = (
            None
            if data.muscle_soreness_0_10 is None
            else 100.0 - data.muscle_soreness_0_10 * 10.0
        )
        vo2_score = _ratio_score(data.vo2max, data.vo2max_baseline)

        recovery_score, recovery_confidence = _weighted_average(
            [
                (autonomic_score if autonomic_confidence else None, 0.32),
                (sleep_score if sleep_confidence else None, 0.28),
                (stress_score, 0.14),
                (fatigue_input_score, 0.16),
                (soreness_score, 0.10),
            ]
        )

        readiness_score, readiness_confidence = _weighted_average(
            [
                (recovery_score if recovery_confidence else None, 0.55),
                (load_score if load_confidence else None, 0.25),
                (vo2_score, 0.10),
                (soreness_score, 0.10),
            ]
        )

        # La douleur forte et les signes infectieux priment sur les moyennes.
        alerts: list[str] = []
        if data.pain_0_10 is not None and data.pain_0_10 >= 7:
            readiness_score = min(readiness_score, 30.0)
            alerts.append("Douleur importante signalee (7/10 ou plus).")
        if data.illness_symptoms:
            readiness_score = min(readiness_score, 20.0)
            alerts.append("Symptomes de maladie signales.")

        confidence = _weighted_average(
            [
                (autonomic_confidence, 0.30),
                (sleep_confidence, 0.25),
                (load_confidence, 0.20),
                (recovery_confidence, 0.15),
                (readiness_confidence, 0.10),
            ]
        )[0]
        status, risk, recommendation = self._decision(readiness_score, alerts)
        explanations = self._explain(
            data, hrv_score, resting_hr_score, sleep_score, load_ratio, readiness_score
        )

        return PhysiologyResult(
            recovery_score=round(recovery_score, 1),
            fatigue_score=round(100.0 - recovery_score, 1),
            readiness_score=round(readiness_score, 1),
            sleep_score=round(sleep_score, 1),
            autonomic_score=round(autonomic_score, 1),
            load_score=round(load_score, 1),
            data_confidence=round(confidence, 1),
            status=status,
            risk_level=risk,
            recommendation=recommendation,
            alerts=alerts,
            explanations=explanations,
            metrics={
                "hrv_score": self._round_or_none(hrv_score),
                "resting_hr_score": self._round_or_none(resting_hr_score),
                "acute_chronic_load_ratio": self._round_or_none(load_ratio, 2),
                "vo2max": data.vo2max,
                "engine_version": self.VERSION,
            },
        )

    def _load_score(self, ratio: Number) -> float:
        if ratio is None:
            return 50.0
        if 0.80 <= ratio <= 1.30:
            return 90.0
        if 0.60 <= ratio < 0.80 or 1.30 < ratio <= 1.50:
            return 65.0
        if 0.40 <= ratio < 0.60 or 1.50 < ratio <= 1.70:
            return 40.0
        return 20.0

    def _decision(self, readiness: float, alerts: list[str]) -> tuple[str, str, str]:
        if alerts or readiness < 35:
            return (
                "RECUPERATION",
                "ELEVE",
                "Repos ou activite tres douce. Reevaluer les symptomes avant tout effort.",
            )
        if readiness < 55:
            return (
                "PRUDENCE",
                "MODERE",
                "Alleger la seance : endurance facile, mobilite et recuperation.",
            )
        if readiness < 75:
            return (
                "DISPONIBLE",
                "FAIBLE_A_MODERE",
                "Entrainement normal possible, avec intensite controlee.",
            )
        return (
            "PRET",
            "FAIBLE",
            "Bonne disponibilite physiologique pour la seance planifiee.",
        )

    def _explain(
        self,
        data: PhysiologyInput,
        hrv_score: Number,
        resting_hr_score: Number,
        sleep_score: float,
        load_ratio: Number,
        readiness: float,
    ) -> list[str]:
        messages = [f"Disponibilite quotidienne estimee a {readiness:.0f}/100."]
        if hrv_score is not None:
            messages.append(
                "HRV favorable par rapport a l'habitude."
                if hrv_score >= 60
                else "HRV inferieure a l'habitude : recuperation autonome a surveiller."
            )
        if resting_hr_score is not None and resting_hr_score < 45:
            messages.append("Frequence cardiaque de repos plus elevee que l'habitude.")
        if data.sleep_hours is not None:
            messages.append(f"Sommeil : {data.sleep_hours:.1f} h, score {sleep_score:.0f}/100.")
        if load_ratio is not None:
            messages.append(f"Rapport charge aigue/chronique : {load_ratio:.2f}.")
        if data.notes:
            messages.append(f"Note utilisateur : {data.notes}")
        return messages

    def _validate(self, data: PhysiologyInput) -> None:
        for name in ("stress_0_10", "subjective_fatigue_0_10", "muscle_soreness_0_10", "pain_0_10"):
            value = getattr(data, name)
            if value is not None and not 0 <= value <= 10:
                raise ValueError(f"{name} doit etre compris entre 0 et 10.")
        if data.sleep_quality_0_100 is not None and not 0 <= data.sleep_quality_0_100 <= 100:
            raise ValueError("sleep_quality_0_100 doit etre compris entre 0 et 100.")
        for name in ("hrv_ms", "hrv_baseline_ms", "resting_hr_bpm", "resting_hr_baseline_bpm", "sleep_hours", "sleep_need_hours", "acute_load_7d", "chronic_load_28d", "vo2max", "vo2max_baseline"):
            value = getattr(data, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} ne peut pas etre negatif.")

    @staticmethod
    def _round_or_none(value: Number, digits: int = 1) -> Number:
        return None if value is None else round(value, digits)


if __name__ == "__main__":
    # Exemple executable : python -m src.physiology.physiology_engine
    example = PhysiologyInput(
        hrv_ms=42,
        hrv_baseline_ms=48,
        resting_hr_bpm=56,
        resting_hr_baseline_bpm=53,
        sleep_hours=6.8,
        sleep_quality_0_100=72,
        stress_0_10=4,
        subjective_fatigue_0_10=3,
        muscle_soreness_0_10=2,
        acute_load_7d=420,
        chronic_load_28d=390,
        vo2max=51,
        vo2max_baseline=50,
        pain_0_10=2,
    )
    result = PhysiologyEngine().analyze(example)
    print(result.to_dict())
