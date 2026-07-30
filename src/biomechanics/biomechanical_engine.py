"""
ATLAS OS
Orchestrateur du moteur biomécanique.
"""

from dataclasses import dataclass, field
from typing import Any, List

from src.biomechanics.exercise_engine import (
    BiomechanicalExercise,
    ExerciseEngine,
)
from src.biomechanics.joint_analyzer import (
    JointAnalyzer,
    JointFinding,
)
from src.biomechanics.kinetic_chain import (
    KineticChainAnalyzer,
    KineticChainFinding,
)
from src.biomechanics.muscle_analyzer import (
    MuscleAnalyzer,
    MuscleFinding,
)
from src.biomechanics.pain_mapper import (
    PainMapper,
    PainMappingResult,
)
from src.biomechanics.risk_analyzer import (
    BiomechanicalRiskAnalyzer,
    BiomechanicalRiskResult,
)


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — RAPPORT BIOMÉCANIQUE
# ████████████████████████████████████████████████████████████

@dataclass
class PainBiomechanicalAnalysis:
    structure_id: str
    side: str
    intensity: int
    context: str
    mapping: PainMappingResult
    joints: List[JointFinding] = field(default_factory=list)
    muscles: List[MuscleFinding] = field(default_factory=list)
    kinetic_chains: List[KineticChainFinding] = field(
        default_factory=list
    )
    risk: BiomechanicalRiskResult | None = None
    exercises: List[BiomechanicalExercise] = field(
        default_factory=list
    )


@dataclass
class BiomechanicalReport:
    analyses: List[PainBiomechanicalAnalysis]
    global_risk_score: int
    global_risk_level: str
    summary: str
    limitations: List[str] = field(default_factory=list)


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — MOTEUR PRINCIPAL
# ████████████████████████████████████████████████████████████

class BiomechanicalEngine:
    def __init__(self) -> None:
        self.pain_mapper = PainMapper()
        self.joint_analyzer = JointAnalyzer()
        self.muscle_analyzer = MuscleAnalyzer()
        self.kinetic_chain_analyzer = (
            KineticChainAnalyzer()
        )
        self.risk_analyzer = (
            BiomechanicalRiskAnalyzer()
        )
        self.exercise_engine = ExerciseEngine()

    def analyse_twin(
        self,
        twin: Any,
    ) -> BiomechanicalReport:
        pain_records = list(
            getattr(twin, "pain_records", [])
            or []
        )

        history_analysis = getattr(
            twin,
            "history_analysis",
            None,
        )

        active_pains = [
            pain
            for pain in pain_records
            if self._pain_intensity(pain) > 0
        ]

        analyses: List[PainBiomechanicalAnalysis] = []

        for pain in active_pains:
            structure_id = str(
                getattr(
                    pain,
                    "anatomical_structure_id",
                    "unknown_structure",
                )
            )

            intensity = self._pain_intensity(pain)

            side = str(
                getattr(pain, "side", "unknown")
            )

            context = str(
                getattr(pain, "context", "")
            )

            mapping = self.pain_mapper.map_pain(
                structure_id
            )

            joints = self.joint_analyzer.analyse(
                structure_id
            )

            muscles = self.muscle_analyzer.analyse(
                structure_id=structure_id,
                context=context,
            )

            kinetic_chains = (
                self.kinetic_chain_analyzer.analyse(
                    structure_id
                )
            )

            risk = self.risk_analyzer.analyse(
                pain=pain,
                history_analysis=history_analysis,
            )

            exercises = self.exercise_engine.generate(
                structure_id=structure_id,
                pain_intensity=intensity,
                risk_score=risk.score,
            )

            analyses.append(
                PainBiomechanicalAnalysis(
                    structure_id=structure_id,
                    side=side,
                    intensity=intensity,
                    context=context,
                    mapping=mapping,
                    joints=joints,
                    muscles=muscles,
                    kinetic_chains=kinetic_chains,
                    risk=risk,
                    exercises=exercises,
                )
            )

        if analyses:
            global_risk_score = round(
                sum(
                    analysis.risk.score
                    for analysis in analyses
                    if analysis.risk is not None
                )
                / len(analyses)
            )
        else:
            global_risk_score = 5

        global_risk_level = self._risk_level(
            global_risk_score
        )

        summary = self._build_summary(
            analyses=analyses,
            risk_score=global_risk_score,
            risk_level=global_risk_level,
        )

        limitations = [
            (
                "L'analyse repose sur les données déclarées "
                "et ne constitue pas un diagnostic médical."
            ),
            (
                "L'examen clinique, l'imagerie et le contexte "
                "complet ne sont pas encore intégrés."
            ),
        ]

        return BiomechanicalReport(
            analyses=analyses,
            global_risk_score=global_risk_score,
            global_risk_level=global_risk_level,
            summary=summary,
            limitations=limitations,
        )

    def display_report(
        self,
        report: BiomechanicalReport,
    ) -> None:
        print("=" * 60)
        print("ATLAS BIOMECHANICS")
        print("=" * 60)

        print(report.summary)

        print()
        print(
            "RISQUE BIOMÉCANIQUE GLOBAL : "
            f"{report.global_risk_score}/100 "
            f"({report.global_risk_level})"
        )

        if not report.analyses:
            print()
            print(
                "Aucune douleur active à analyser."
            )

        for index, analysis in enumerate(
            report.analyses,
            start=1,
        ):
            print()
            print("-" * 60)
            print(
                f"ANALYSE {index} — "
                f"{analysis.mapping.display_name}"
            )
            print("-" * 60)

            print(
                f"Structure : {analysis.structure_id}"
            )
            print(
                f"Côté : {analysis.side}"
            )
            print(
                f"Intensité : {analysis.intensity}/10"
            )

            if analysis.context:
                print(
                    f"Contexte : {analysis.context}"
                )

            if analysis.risk is not None:
                print(
                    "Risque local : "
                    f"{analysis.risk.score}/100 "
                    f"({analysis.risk.level})"
                )

            print()
            print("STRUCTURES ASSOCIÉES")

            for structure in (
                analysis.mapping.related_structures
            ):
                print(f"  • {structure}")

            print()
            print("MÉCANISMES POSSIBLES")

            for mechanism in (
                analysis.mapping.possible_mechanisms
            ):
                print(f"  • {mechanism}")

            print()
            print("ARTICULATIONS À ÉVALUER")

            for joint in analysis.joints:
                print(
                    f"  • {joint.joint_name} "
                    f"({joint.relevance_score} %)"
                )

            print()
            print("MUSCLES À ÉVALUER")

            for muscle in analysis.muscles:
                print(
                    f"  • {muscle.muscle_name} "
                    f"({muscle.relevance_score} %)"
                )

            print()
            print("CHAÎNES CINÉTIQUES")

            for chain in analysis.kinetic_chains:
                print(
                    f"  • {chain.chain_name} "
                    f"({chain.relevance_score} %)"
                )

            print()
            print("EXERCICES PROPOSÉS")

            for exercise in analysis.exercises:
                print(f"  • {exercise.name}")
                print(
                    f"    {exercise.instructions}"
                )
                print(
                    f"    Dosage : {exercise.dosage}"
                )

        print()
        print("LIMITES")

        for limitation in report.limitations:
            print(f"  • {limitation}")

        print("=" * 60)

    @staticmethod
    def _pain_intensity(pain: Any) -> int:
        try:
            return max(
                0,
                min(
                    10,
                    int(getattr(pain, "intensity", 0)),
                ),
            )
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _risk_level(score: int) -> str:
        if score >= 70:
            return "élevé"
        if score >= 40:
            return "modéré"
        return "faible"

    @staticmethod
    def _build_summary(
        analyses: List[PainBiomechanicalAnalysis],
        risk_score: int,
        risk_level: str,
    ) -> str:
        if not analyses:
            return (
                "Aucune douleur active n'est actuellement "
                "enregistrée dans le jumeau numérique."
            )

        main_analysis = max(
            analyses,
            key=lambda analysis: analysis.intensity,
        )

        return (
            f"{len(analyses)} douleur(s) active(s) ont été "
            f"analysée(s). La région prioritaire est "
            f"{main_analysis.mapping.display_name.lower()} "
            f"avec une intensité de "
            f"{main_analysis.intensity}/10. "
            f"Le niveau global de vigilance biomécanique "
            f"est {risk_level}, avec un score de "
            f"{risk_score}/100."
        )


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████