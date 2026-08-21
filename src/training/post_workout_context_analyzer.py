"""Interprétation explicable du ressenti déclaré après une séance."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class PostWorkoutContextAnalysis:
    """Proposition prudente produite avant confirmation de la récupération."""

    status: str
    action: str
    next_load_factor: float
    confidence_score: int
    requires_user_validation: bool = True
    requires_recovery_confirmation: bool = True
    external_constraints: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PostWorkoutContextAnalyzer:
    """Sépare contraintes externes, tolérance et signaux biomécaniques."""

    SCORE_FIELDS = (
        "overall_sensation_0_to_10",
        "perceived_effort_0_to_10",
        "heat_0_to_10",
        "relief_0_to_10",
        "pain_0_to_10",
        "fatigue_0_to_10",
    )

    def analyze(self, context: dict[str, Any]) -> PostWorkoutContextAnalysis:
        scores = {
            name: self._score(context.get(name))
            for name in self.SCORE_FIELDS
        }
        sensation = scores["overall_sensation_0_to_10"]
        effort = scores["perceived_effort_0_to_10"]
        heat = scores["heat_0_to_10"]
        relief = scores["relief_0_to_10"]
        pain = scores["pain_0_to_10"]
        fatigue = scores["fatigue_0_to_10"]
        answered = sum(value is not None for value in scores.values())
        confidence = round(answered / len(scores) * 85)
        if str(context.get("comment") or "").strip():
            confidence = min(100, confidence + 10)

        external: list[str] = []
        reasons: list[str] = []
        if heat is not None and heat >= 5:
            external.append(f"Chaleur ressentie {heat}/10")
        if relief is not None and relief >= 5:
            external.append(f"Relief contraignant {relief}/10")
        if external:
            reasons.append(
                "Les contraintes externes contextualisent le coût cardiaque "
                "sans être interprétées seules comme une baisse de forme."
            )

        if pain is not None and pain >= 7:
            reasons.append(
                f"Douleur élevée ({pain}/10) : priorité à la récupération "
                "et à la réévaluation avant la prochaine intensité."
            )
            return self._result("alert", "recovery_priority", .65, confidence, external, reasons)

        if fatigue is not None and fatigue >= 8:
            reasons.append(
                f"Fatigue élevée ({fatigue}/10) : la prochaine charge "
                "intensive doit être allégée ou différée."
            )
            return self._result("alert", "recovery_priority", .7, confidence, external, reasons)

        warning = any((
            pain is not None and pain >= 4,
            fatigue is not None and fatigue >= 6,
            effort is not None and effort >= 9,
            sensation is not None and sensation <= 3,
        ))
        if warning:
            reasons.append(
                "La réponse subjective est moins favorable qu’attendu : "
                "Atlas propose une réduction provisoire de la prochaine intensité."
            )
            return self._result("caution", "reduce_next_intensity", .85, confidence, external, reasons)

        positive = all((
            sensation is not None and sensation >= 7,
            effort is not None and effort <= 7,
            pain is not None and pain <= 2,
            fatigue is not None and fatigue <= 4,
        ))
        if positive:
            reasons.append(
                "La séance paraît bien tolérée. Le maintien du programme est "
                "proposé, sous réserve de la récupération à 24–72 heures."
            )
            return self._result("positive", "maintain", 1.0, confidence, external, reasons)

        reasons.append(
            "Aucun signal isolé ne justifie une modification immédiate. "
            "Atlas maintient la séance suivante sous surveillance."
        )
        return self._result("stable", "monitor", .95, confidence, external, reasons)

    @staticmethod
    def _score(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        score = int(value)
        return score if 0 <= score <= 10 else None

    @staticmethod
    def _result(status, action, factor, confidence, external, reasons):
        return PostWorkoutContextAnalysis(
            status=status,
            action=action,
            next_load_factor=factor,
            confidence_score=confidence,
            external_constraints=external,
            reasons=reasons,
        )
