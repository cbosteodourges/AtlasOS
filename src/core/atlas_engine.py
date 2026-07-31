"""
ATLAS OS
Moteur principal.
"""


# ████████████████████████████████████████████████████████████
# ⬜ PARTIE IMPORTS
# ████████████████████████████████████████████████████████████

from datetime import date, datetime, timedelta

from src.anatomy import build_right_ankle_foot
from src.atlas_brain import AtlasBrain
from src.biomechanics import BiomechanicalEngine
from src.core.config import Config
from src.core.logger import AtlasLogger
from src.core.version import APP_NAME, VERSION
from src.patient.patient import Patient
from src.performance import (
    PerformanceGoal,
    RunningPlanGenerator,
    TrainingActivity,
    TrainingHistoryAnalyzer,
    TrainingZonesEngine,
    display_history_analysis,
    display_training_plan,
)
from src.physiology import PhysiologyEngine, PhysiologyInput, PhysiologyResult
from src.twin import DigitalTwin


# ████████████████████████████████████████████████████████████
# ⬜ FIN PARTIE IMPORTS
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — INITIALISATION
# ████████████████████████████████████████████████████████████

class AtlasEngine:
    def __init__(self) -> None:
        self.start_time = datetime.now()

        self.user = Patient(
            nom="Bonnet",
            prenom="Christophe",
            age=50,
            sexe="Homme",
            taille=1.86,
            poids=98,
            frequence_cardiaque=52,
            hrv=61,
            vo2max=51,
        )

        self.maximum_heart_rate = 185
        self.vma_kmh = 14.0

        self.anatomy = build_right_ankle_foot()

        self.history_analyzer = TrainingHistoryAnalyzer()
        self.zones_engine = TrainingZonesEngine()
        self.plan_generator = RunningPlanGenerator()

        self.twin = DigitalTwin(user=self.user)

        self.biomechanical_engine = BiomechanicalEngine()
        self.physiology_engine = PhysiologyEngine()
        self.brain = AtlasBrain()


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — HISTORIQUE DE DÉMONSTRATION
# ████████████████████████████████████████████████████████████

    def build_demo_history(self):
        today = date.today()

        demo_values = [
            (27, 8, 48, 136, 4),
            (24, 10, 58, 139, 5),
            (21, 14, 84, 141, 5),
            (18, 9, 52, 143, 5),
            (15, 11, 62, 146, 6),
            (13, 7, 38, 154, 8),
            (10, 16, 96, 142, 6),
            (7, 8, 46, 140, 4),
            (5, 10, 55, 148, 6),
            (2, 17, 102, 144, 6),
        ]

        activities = []

        for (
            days_ago,
            distance,
            duration,
            average_hr,
            rpe,
        ) in demo_values:
            activities.append(
                TrainingActivity(
                    activity_date=today - timedelta(days=days_ago),
                    activity_type="running",
                    distance_km=distance,
                    duration_minutes=duration,
                    average_heart_rate=average_hr,
                    perceived_exertion=rpe,
                )
            )

        return activities


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟨 PARTIE C — PERFORMANCE
# ████████████████████████████████████████████████████████████

    def build_performance_data(self):
        activities = self.build_demo_history()

        analysis = self.history_analyzer.analyse(activities)

        zones = self.zones_engine.calculate(
            maximum_heart_rate=self.maximum_heart_rate,
            vma_kmh=self.vma_kmh,
        )

        goal = PerformanceGoal(
            name="Semi-marathon",
            event_date=date.today() + timedelta(days=90),
            distance_km=21.1,
            target_time_minutes=106,
        )

        plan = self.plan_generator.generate(
            goal=goal,
            analysis=analysis,
            weeks_count=4,
        )

        return analysis, zones, plan


# ████████████████████████████████████████████████████████████
# 🟨 FIN PARTIE C
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟧 PARTIE D — DIGITAL TWIN
# ████████████████████████████████████████████████████████████

    def build_digital_twin(self, analysis, plan) -> None:
        self.twin.attach_anatomy(self.anatomy)
        self.twin.attach_history_analysis(analysis)
        self.twin.attach_training_plan(plan)

        self.twin.update_metric(
            metric_name="maximum_heart_rate",
            value=self.maximum_heart_rate,
            source="manual_profile",
        )

        self.twin.update_metric(
            metric_name="vma_kmh",
            value=self.vma_kmh,
            source="manual_profile",
        )

        self.twin.add_pain(
            anatomical_structure_id="tendon.achilles.right",
            intensity=2,
            side="right",
            description="Sensibilité légère après une sortie longue.",
            context="running",
        )


# ████████████████████████████████████████████████████████████
# 🟧 FIN PARTIE D
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟪 PARTIE E — PHYSIOLOGIE
# ████████████████████████████████████████████████████████████

    def build_physiology_data(self) -> PhysiologyResult:
        """Analyse les données physiologiques quotidiennes de démonstration."""
        physiology_data = PhysiologyInput(
            hrv_ms=61,
            hrv_baseline_ms=55,
            resting_hr_bpm=52,
            resting_hr_baseline_bpm=54,
            sleep_hours=7.4,
            sleep_need_hours=8.0,
            sleep_quality_0_100=82,
            stress_0_10=3,
            subjective_fatigue_0_10=3,
            muscle_soreness_0_10=2,
            acute_load_7d=420,
            chronic_load_28d=390,
            vo2max=51,
            vo2max_baseline=50,
            pain_0_10=2,
            illness_symptoms=False,
            notes="Données de démonstration ATLAS OS.",
        )

        result = self.physiology_engine.analyze(physiology_data)

        self.twin.update_metric(
            metric_name="physiology_recovery_score",
            value=result.recovery_score,
            source="physiology_engine_0.6",
        )
        self.twin.update_metric(
            metric_name="physiology_fatigue_score",
            value=result.fatigue_score,
            source="physiology_engine_0.6",
        )
        self.twin.update_metric(
            metric_name="physiology_readiness_score",
            value=result.readiness_score,
            source="physiology_engine_0.6",
        )
        self.twin.update_metric(
            metric_name="physiology_sleep_score",
            value=result.sleep_score,
            source="physiology_engine_0.6",
        )

        return result

    def display_physiology_report(self, result: PhysiologyResult) -> None:
        print("=" * 60)
        print("ATLAS PHYSIOLOGY ENGINE")
        print("=" * 60)
        print(f"Récupération          : {result.recovery_score}/100")
        print(f"Fatigue               : {result.fatigue_score}/100")
        print(f"Disponibilité         : {result.readiness_score}/100")
        print(f"Sommeil               : {result.sleep_score}/100")
        print(f"Système autonome      : {result.autonomic_score}/100")
        print(f"Charge                : {result.load_score}/100")
        print(f"Confiance des données : {result.data_confidence}%")
        print(f"Statut                : {result.status}")
        print(f"Niveau de risque      : {result.risk_level}")
        print(f"Recommandation        : {result.recommendation}")

        if result.alerts:
            print("Alertes :")
            for alert in result.alerts:
                print(f"  - {alert}")

        print("Explications :")
        for explanation in result.explanations:
            print(f"  - {explanation}")
        print("=" * 60)


# ████████████████████████████████████████████████████████████
# 🟪 FIN PARTIE E
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟥 PARTIE F — DÉMARRAGE
# ████████████████████████████████████████████████████████████

    def start(self) -> None:
        AtlasLogger.info("Initialisation du moteur ATLAS")

        print("=" * 60)
        print(APP_NAME)
        print(f"Version : {VERSION}")
        print(f"Démarré : {self.start_time}")
        print("=" * 60)

        Config.afficher()
        AtlasLogger.info("Configuration chargée")

        print()
        self.user.afficher()
        AtlasLogger.info("Utilisateur chargé")

        print()
        self.anatomy.display_summary()
        AtlasLogger.info("Modèle anatomique chargé")

        analysis, zones, plan = self.build_performance_data()

        print()
        display_history_analysis(analysis)

        print()
        self.zones_engine.display(zones)

        print()
        display_training_plan(plan)
        AtlasLogger.info("Moteur Performance chargé")

        self.build_digital_twin(analysis=analysis, plan=plan)

        print()
        self.twin.display_summary()
        AtlasLogger.info("Jumeau numérique chargé")

        physiology_report = self.build_physiology_data()

        print()
        self.display_physiology_report(physiology_report)
        AtlasLogger.info("Moteur physiologique chargé")

        biomechanical_report = self.biomechanical_engine.analyse_twin(self.twin)

        print()
        self.biomechanical_engine.display_report(biomechanical_report)
        AtlasLogger.info("Moteur biomécanique chargé")

        brain_report = self.brain.analyse(self.twin)

        print()
        self.brain.display_report(brain_report)
        AtlasLogger.info("Atlas Brain chargé")

        AtlasLogger.info("ATLAS est opérationnel")


# ████████████████████████████████████████████████████████████
# 🟥 FIN PARTIE F
# ████████████████████████████████████████████████████████████
