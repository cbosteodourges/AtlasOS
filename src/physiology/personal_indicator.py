"""Contrat commun d'interprétation longitudinale des indicateurs Atlas."""

from __future__ import annotations

from typing import Any


class PersonalIndicatorInterpreter:
    """Transforme une mesure en décision personnelle explicable.

    Chaque résultat répond obligatoirement aux cinq questions Atlas :
    référence, zone optimale, évolution, conséquence et recommandation.
    """

    @staticmethod
    def interpret(
        *,
        indicator: str,
        current: dict[str, Any],
        personal_reference: str,
        optimal_zone: str,
        evolution: str,
        probable_consequence: str,
        recommendation: str,
        favorability_score: float | None,
        confidence: int,
        data_complete: bool,
        missing_data: list[str] | None = None,
    ) -> dict[str, Any]:
        score = (
            max(0.0, min(100.0, float(favorability_score)))
            if favorability_score is not None else None
        )
        confidence = max(0, min(100, int(confidence)))
        missing = list(missing_data or [])

        if score is None or confidence < 45:
            status = "monitor"
            status_label = "À surveiller"
            display_label = "Données insuffisantes"
        elif score < 55:
            status = "vigilance"
            status_label = "Vigilance"
            display_label = "Récupération insuffisante probable"
        elif score >= 85 and data_complete and confidence >= 80:
            status = "optimal"
            status_label = "Optimal"
            display_label = "Conditions optimales"
        else:
            status = "monitor"
            status_label = "À surveiller"
            if score >= 85:
                display_label = "Bonne récupération probable"
            elif score >= 70:
                display_label = "Récupération favorable probable"
            else:
                display_label = "Récupération intermédiaire"

        if not data_complete and missing:
            display_label += " · à confirmer"

        return {
            "indicator": indicator,
            "status": status,
            "status_label": status_label,
            "display_label": display_label,
            "current": current,
            "personal_reference": personal_reference,
            "optimal_zone": optimal_zone,
            "evolution": evolution,
            "probable_consequence": probable_consequence,
            "recommendation": recommendation,
            "confidence": confidence,
            "data_complete": bool(data_complete),
            "missing_data": missing,
            "five_questions": {
                "reference": personal_reference,
                "optimal": optimal_zone,
                "evolution": evolution,
                "consequence": probable_consequence,
                "advice": recommendation,
            },
        }
