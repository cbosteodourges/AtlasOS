"""
ATLAS OS
Module central Atlas Brain.
"""

from dataclasses import dataclass
from typing import List

from src.atlas_brain.alerts import (
    AtlasAlert,
    AtlasAlertEngine,
)
from src.atlas_brain.diagnosis import (
    AtlasHypothesis,
    AtlasHypothesisEngine,
)
from src.atlas_brain.explanation import (
    AtlasExplanationEngine,
)
from src.atlas_brain.reasoning import (
    AtlasReasoningEngine,
    ReasoningResult,
)
from src.atlas_brain.recommendations import (
    AtlasRecommendation,
    AtlasRecommendationEngine,
)
from src.twin import DigitalTwin


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — RAPPORT ATLAS BRAIN
# ████████████████████████████████████████████████████████████

@dataclass
class AtlasBrainReport:
    reasoning: ReasoningResult
    hypotheses: List[AtlasHypothesis]
    alerts: List[AtlasAlert]
    recommendations: List[
        AtlasRecommendation
    ]
    summary: str
    detailed_explanation: List[str]


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — ORCHESTRATEUR ATLAS BRAIN
# ████████████████████████████████████████████████████████████

class AtlasBrain:
    def __init__(self) -> None:
        self.reasoning_engine = (
            AtlasReasoningEngine()
        )

        self.hypothesis_engine = (
            AtlasHypothesisEngine()
        )

        self.alert_engine = (
            AtlasAlertEngine()
        )

        self.recommendation_engine = (
            AtlasRecommendationEngine()
        )

        self.explanation_engine = (
            AtlasExplanationEngine()
        )

    def analyse(
        self,
        twin: DigitalTwin,
    ) -> AtlasBrainReport:
        reasoning = (
            self.reasoning_engine.analyse(
                twin
            )
        )

        hypotheses = (
            self.hypothesis_engine.generate(
                reasoning
            )
        )

        alerts = (
            self.alert_engine.generate(
                reasoning
            )
        )

        recommendations = (
            self.recommendation_engine.generate(
                reasoning,
                alerts,
            )
        )

        summary = (
            self.explanation_engine.build_summary(
                first_name=twin.user.prenom,
                reasoning=reasoning,
                hypotheses=hypotheses,
                alerts=alerts,
                recommendations=recommendations,
            )
        )

        detailed_explanation = (
            self.explanation_engine
            .build_detailed_explanation(
                reasoning=reasoning,
                recommendations=recommendations,
            )
        )

        return AtlasBrainReport(
            reasoning=reasoning,
            hypotheses=hypotheses,
            alerts=alerts,
            recommendations=recommendations,
            summary=summary,
            detailed_explanation=(
                detailed_explanation
            ),
        )

    def display_report(
        self,
        report: AtlasBrainReport,
    ) -> None:
        print("=" * 60)
        print("ATLAS BRAIN")
        print("=" * 60)

        print(report.summary)

        print()
        print("SCORES")

        print(
            "Disponibilité : "
            f"{report.reasoning.readiness_score}/100"
        )

        print(
            "Récupération : "
            f"{report.reasoning.recovery_score}/100"
        )

        print(
            "Vigilance mécanique : "
            f"{report.reasoning.mechanical_risk_score}/100"
        )

        print(
            "Confiance des données : "
            f"{report.reasoning.data_confidence_score}/100"
        )

        print()
        print("HYPOTHÈSES")

        for hypothesis in report.hypotheses:
            print(
                f"  ? {hypothesis.title} "
                f"({hypothesis.probability} %)"
            )
            print(
                f"    {hypothesis.explanation}"
            )

        print()
        print("ALERTES")

        if not report.alerts:
            print(
                "  Aucune alerte majeure."
            )

        for alert in report.alerts:
            print(
                f"  ! [{alert.level.upper()}] "
                f"{alert.title}"
            )
            print(
                f"    {alert.message}"
            )

        print()
        print("RECOMMANDATIONS")

        for recommendation in (
            report.recommendations
        ):
            print(
                f"  {recommendation.priority}. "
                f"{recommendation.title}"
            )
            print(
                f"     {recommendation.description}"
            )
            print(
                f"     Pourquoi : "
                f"{recommendation.reason}"
            )
            print(
                f"     Confiance : "
                f"{recommendation.confidence} %"
            )

        print()
        print("EXPLICATION")

        for paragraph in (
            report.detailed_explanation
        ):
            print(
                f"  {paragraph}"
            )

        print("=" * 60)


__all__ = [
    "AtlasAlert",
    "AtlasBrain",
    "AtlasBrainReport",
    "AtlasHypothesis",
    "AtlasRecommendation",
    "ReasoningResult",
]


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████