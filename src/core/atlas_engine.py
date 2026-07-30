"""
ATLAS OS
Moteur principal.
"""

from datetime import date, datetime, timedelta

from src.anatomy import build_right_ankle_foot
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
from src.twin import DigitalTwin


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — INITIALISATION
# ████████████████████████████████████████████████████████████

class AtlasEngine:
    def __init__(self):
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

        self.anatomy = (
            build_right_ankle_foot()
        )

        self.history_analyzer = (
            TrainingHistoryAnalyzer()
        )

        self.zones_engine = (
            TrainingZonesEngine()
        )

        self.plan_generator = (
            RunningPlanGenerator()
        )

        self.twin = DigitalTwin(
            user=self.user
        )


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — HISTORIQUE DE DÉMONSTRATION
# ████████████████████████████████████████████████████████████

    def build_demo_history(self):
        today = date.today()

        return [
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=27)
                ),
                activity_type="running",
                distance_km=8,
                duration_minutes=48,
                average_heart_rate=136,
                perceived_exertion=4,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=24)
                ),
                activity_type="running",
                distance_km=10,
                duration_minutes=58,
                average_heart_rate=139,
                perceived_exertion=5,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=21)
                ),
                activity_type="running",
                distance_km=14,
                duration_minutes=84,
                average_heart_rate=141,
                perceived_exertion=5,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=18)
                ),
                activity_type="running",
                distance_km=9,
                duration_minutes=52,
                average_heart_rate=143,
                perceived_exertion=5,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=15)
                ),
                activity_type="running",
                distance_km=11,
                duration_minutes=62,
                average_heart_rate=146,
                perceived_exertion=6,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=13)
                ),
                activity_type="running",
                distance_km=7,
                duration_minutes=38,
                average_heart_rate=154,
                perceived_exertion=8,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=10)
                ),
                activity_type="running",
                distance_km=16,
                duration_minutes=96,
                average_heart_rate=142,
                perceived_exertion=6,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=7)
                ),
                activity_type="running",
                distance_km=8,
                duration_minutes=46,
                average_heart_rate=140,
                perceived_exertion=4,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=5)
                ),
                activity_type="running",
                distance_km=10,
                duration_minutes=55,
                average_heart_rate=148,
                perceived_exertion=6,
            ),
            TrainingActivity(
                activity_date=(
                    today - timedelta(days=2)
                ),
                activity_type="running",
                distance_km=17,
                duration_minutes=102,
                average_heart_rate=144,
                perceived_exertion=6,
            ),
        ]


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟨 PARTIE C — PERFORMANCE
# ████████████████████████████████████████████████████████████

    def build_performance_data(self):
        activities = (
            self.build_demo_history()
        )

        analysis = (
            self.history_analyzer.analyse(
                activities
            )
        )

        zones = self.zones_engine.calculate(
            maximum_heart_rate=(
                self.maximum_heart_rate
            ),
            vma_kmh=self.vma_kmh,
        )

        goal = PerformanceGoal(
            name="Semi-marathon",
            event_date=(
                date.today()
                + timedelta(days=90)
            ),
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
# 🟧 PARTIE D — CONSTRUCTION DU JUMEAU
# ████████████████████████████████████████████████████████████

    def build_digital_twin(
        self,
        analysis,
        plan,
    ):
        self.twin.attach_anatomy(
            self.anatomy
        )

        self.twin.attach_history_analysis(
            analysis
        )

        self.twin.attach_training_plan(
            plan
        )

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
            anatomical_structure_id=(
                "tendon.achilles.right"
            ),
            intensity=2,
            side="right",
            description=(
                "Sensibilité légère après "
                "une sortie longue."
            ),
            context="running",
        )


# ████████████████████████████████████████████████████████████
# 🟧 FIN PARTIE D
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟥 PARTIE E — DÉMARRAGE
# ████████████████████████████████████████████████████████████

    def start(self):
        AtlasLogger.info(
            "Initialisation du moteur ATLAS"
        )

        print("=" * 60)
        print(APP_NAME)
        print(f"Version : {VERSION}")
        print(f"Démarré : {self.start_time}")
        print("=" * 60)

        Config.afficher()

        AtlasLogger.info(
            "Configuration chargée"
        )

        print()

        self.user.afficher()

        AtlasLogger.info(
            "Utilisateur chargé"
        )

        print()

        self.anatomy.display_summary()

        AtlasLogger.info(
            "Modèle anatomique chargé"
        )

        analysis, zones, plan = (
            self.build_performance_data()
        )

        print()

        display_history_analysis(
            analysis
        )

        print()

        self.zones_engine.display(
            zones
        )

        print()

        display_training_plan(
            plan
        )

        AtlasLogger.info(
            "Moteur Performance chargé"
        )

        self.build_digital_twin(
            analysis=analysis,
            plan=plan,
        )

        print()

        self.twin.display_summary()

        AtlasLogger.info(
            "Jumeau numérique chargé"
        )

        AtlasLogger.info(
            "ATLAS est opérationnel"
        )


# ████████████████████████████████████████████████████████████
# 🟥 FIN PARTIE E
# ████████████████████████████████████████████████████████████