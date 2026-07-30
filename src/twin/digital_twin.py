"""
ATLAS OS
Jumeau numérique central de l'utilisateur.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.events import events
from src.patient.patient import Patient
from src.performance.models import (
    HistoryAnalysis,
    TrainingPlan,
)


# ████████████████████████████████████████████████████████████
# 🟦 PARTIE A — ENREGISTREMENT D'UNE DOULEUR
# ████████████████████████████████████████████████████████████

@dataclass
class PainRecord:
    """
    Représente une douleur déclarée par l'utilisateur.

    Ce modèle ne pose aucun diagnostic.
    Il conserve uniquement les informations renseignées.
    """

    anatomical_structure_id: str
    intensity: int
    side: str = "unknown"
    description: str = ""
    irradiation: str = ""
    context: str = ""
    recorded_at: datetime = field(
        default_factory=datetime.now
    )

    def __post_init__(self) -> None:
        if not 0 <= self.intensity <= 10:
            raise ValueError(
                "L'intensité de la douleur doit être comprise "
                "entre 0 et 10."
            )


# ████████████████████████████████████████████████████████████
# 🟦 FIN PARTIE A
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟩 PARTIE B — ÉTAT DU JUMEAU NUMÉRIQUE
# ████████████████████████████████████████████████████████████

@dataclass
class TwinState:
    """
    Résumé de l'état courant du jumeau numérique.
    """

    status: str = "initializing"
    created_at: datetime = field(
        default_factory=datetime.now
    )
    updated_at: datetime = field(
        default_factory=datetime.now
    )

    data_sources: List[str] = field(
        default_factory=list
    )

    warnings: List[str] = field(
        default_factory=list
    )

    notes: List[str] = field(
        default_factory=list
    )


# ████████████████████████████████████████████████████████████
# 🟩 FIN PARTIE B
# ████████████████████████████████████████████████████████████


# ████████████████████████████████████████████████████████████
# 🟨 PARTIE C — JUMEAU NUMÉRIQUE ATLAS
# ████████████████████████████████████████████████████████████

class DigitalTwin:
    """
    Point central des données personnelles d'ATLAS OS.

    Le DigitalTwin conserve les références vers les différents
    moteurs et modèles de l'utilisateur sans dupliquer leurs données.
    """

    def __init__(
        self,
        user: Patient,
    ) -> None:
        self.user = user

        self.anatomy: Optional[Any] = None

        self.history_analysis: Optional[
            HistoryAnalysis
        ] = None

        self.training_plan: Optional[
            TrainingPlan
        ] = None

        self.physiological_metrics: Dict[
            str,
            float
        ] = {}

        self.pain_records: List[
            PainRecord
        ] = []

        self.state = TwinState(
            status="ready"
        )

        self._register_initial_profile()

        events.emit(
            "twin.created",
            self,
        )

    def _register_initial_profile(self) -> None:
        """
        Intègre au jumeau les données déjà présentes
        dans le profil utilisateur.
        """

        initial_metrics = {
            "heart_rate": (
                self.user.frequence_cardiaque
            ),
            "hrv": self.user.hrv,
            "vo2max": self.user.vo2max,
            "weight_kg": self.user.poids,
            "height_m": self.user.taille,
            "bmi": self.user.imc,
        }

        for name, value in initial_metrics.items():
            if value not in (None, 0, 0.0):
                self.physiological_metrics[
                    name
                ] = float(value)

        self._add_data_source(
            "manual_profile"
        )

        self._touch()

    def _touch(self) -> None:
        """
        Met à jour la date de dernière modification.
        """

        self.state.updated_at = datetime.now()

    def _add_data_source(
        self,
        source_name: str,
    ) -> None:
        """
        Enregistre une source de données sans doublon.
        """

        if source_name not in self.state.data_sources:
            self.state.data_sources.append(
                source_name
            )

    def attach_anatomy(
        self,
        anatomy_registry: Any,
    ) -> None:
        """
        Relie le registre anatomique au jumeau.
        """

        self.anatomy = anatomy_registry

        self._add_data_source(
            "atlas_anatomy"
        )

        self._touch()

        events.emit(
            "twin.anatomy_attached",
            anatomy_registry,
        )

    def attach_history_analysis(
        self,
        analysis: HistoryAnalysis,
    ) -> None:
        """
        Relie l'analyse de l'historique sportif.
        """

        self.history_analysis = analysis

        self._add_data_source(
            "training_history"
        )

        self._touch()

        events.emit(
            "twin.history_updated",
            analysis,
        )

    def attach_training_plan(
        self,
        plan: TrainingPlan,
    ) -> None:
        """
        Relie le plan d'entraînement courant.
        """

        self.training_plan = plan

        self._add_data_source(
            "atlas_performance"
        )

        self._touch()

        events.emit(
            "twin.training_plan_updated",
            plan,
        )

    def update_metric(
        self,
        metric_name: str,
        value: float,
        source: str = "manual",
    ) -> None:
        """
        Ajoute ou modifie un indicateur physiologique.

        Exemples :
        - hrv
        - resting_heart_rate
        - sleep_duration_hours
        - stress_score
        - training_load
        """

        if not metric_name.strip():
            raise ValueError(
                "Le nom de l'indicateur est obligatoire."
            )

        self.physiological_metrics[
            metric_name
        ] = float(value)

        self._add_data_source(
            source
        )

        self._touch()

        events.emit(
            "twin.metric_updated",
            {
                "name": metric_name,
                "value": value,
                "source": source,
            },
        )

    def get_metric(
        self,
        metric_name: str,
    ) -> Optional[float]:
        """
        Retourne un indicateur physiologique.
        """

        return self.physiological_metrics.get(
            metric_name
        )

    def add_pain(
        self,
        anatomical_structure_id: str,
        intensity: int,
        side: str = "unknown",
        description: str = "",
        irradiation: str = "",
        context: str = "",
    ) -> PainRecord:
        """
        Enregistre une douleur déclarée.
        """

        pain = PainRecord(
            anatomical_structure_id=(
                anatomical_structure_id
            ),
            intensity=intensity,
            side=side,
            description=description,
            irradiation=irradiation,
            context=context,
        )

        self.pain_records.append(
            pain
        )

        self._add_data_source(
            "user_report"
        )

        self._touch()

        events.emit(
            "twin.pain_added",
            pain,
        )

        return pain

    def get_latest_pain(
        self,
        anatomical_structure_id: Optional[
            str
        ] = None,
    ) -> Optional[PainRecord]:
        """
        Retourne la dernière douleur enregistrée.

        Une structure anatomique précise peut être indiquée.
        """

        records = self.pain_records

        if anatomical_structure_id:
            records = [
                record
                for record in records
                if record.anatomical_structure_id
                == anatomical_structure_id
            ]

        if not records:
            return None

        return max(
            records,
            key=lambda record: record.recorded_at,
        )

    def get_profile_completion(self) -> int:
        """
        Calcule un score de complétude des données.

        Ce score ne représente ni la santé ni la performance.
        Il indique seulement si le profil contient suffisamment
        d'informations pour personnaliser ATLAS.
        """

        checks = [
            bool(self.user.nom),
            bool(self.user.prenom),
            self.user.age > 0,
            bool(self.user.sexe),
            self.user.taille > 0,
            self.user.poids > 0,
            self.user.frequence_cardiaque > 0,
            self.user.hrv > 0,
            self.user.vo2max > 0,
            self.anatomy is not None,
            self.history_analysis is not None,
            self.training_plan is not None,
        ]

        completed = sum(
            1
            for check in checks
            if check
        )

        return round(
            completed
            / len(checks)
            * 100
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Produit un résumé exploitable plus tard par :
        - l'interface Web ;
        - Android et iOS ;
        - une API ;
        - le futur Atlas Brain.
        """

        anatomy_count = 0

        if (
            self.anatomy is not None
            and hasattr(
                self.anatomy,
                "count",
            )
        ):
            anatomy_count = (
                self.anatomy.count()
            )

        return {
            "user": {
                "first_name": self.user.prenom,
                "last_name": self.user.nom,
                "age": self.user.age,
                "sex": self.user.sexe,
                "height_m": self.user.taille,
                "weight_kg": self.user.poids,
                "bmi": self.user.imc,
            },
            "twin": {
                "status": self.state.status,
                "created_at": (
                    self.state.created_at.isoformat()
                ),
                "updated_at": (
                    self.state.updated_at.isoformat()
                ),
                "profile_completion": (
                    self.get_profile_completion()
                ),
            },
            "data_sources": list(
                self.state.data_sources
            ),
            "physiological_metrics": dict(
                self.physiological_metrics
            ),
            "anatomy": {
                "connected": (
                    self.anatomy is not None
                ),
                "structure_count": anatomy_count,
            },
            "performance": {
                "history_connected": (
                    self.history_analysis
                    is not None
                ),
                "plan_connected": (
                    self.training_plan
                    is not None
                ),
                "planned_workouts": (
                    self.training_plan.total_workouts
                    if self.training_plan
                    else 0
                ),
            },
            "pain": {
                "record_count": len(
                    self.pain_records
                ),
            },
        }

    def display_summary(self) -> None:
        """
        Affiche l'état courant du jumeau numérique.
        """

        summary = self.get_summary()

        print("=" * 60)
        print("ATLAS DIGITAL TWIN")
        print("=" * 60)

        print(
            "Utilisateur : "
            f"{self.user.prenom} "
            f"{self.user.nom}"
        )

        print(
            f"Statut : "
            f"{self.state.status}"
        )

        print(
            "Profil complété : "
            f"{summary['twin']['profile_completion']} %"
        )

        print(
            "Sources de données : "
            f"{len(self.state.data_sources)}"
        )

        for source in self.state.data_sources:
            print(
                f"  - {source}"
            )

        print()
        print(
            "Indicateurs physiologiques : "
            f"{len(self.physiological_metrics)}"
        )

        for name, value in (
            self.physiological_metrics.items()
        ):
            print(
                f"  - {name} : {value}"
            )

        print()
        print(
            "Structures anatomiques : "
            f"{summary['anatomy']['structure_count']}"
        )

        print(
            "Historique Performance : "
            f"{'chargé' if self.history_analysis else 'absent'}"
        )

        print(
            "Plan d'entraînement : "
            f"{'chargé' if self.training_plan else 'absent'}"
        )

        print(
            "Séances planifiées : "
            f"{summary['performance']['planned_workouts']}"
        )

        print(
            "Douleurs enregistrées : "
            f"{len(self.pain_records)}"
        )

        print("=" * 60)


# ████████████████████████████████████████████████████████████
# 🟨 FIN PARTIE C
# ████████████████████████████████████████████████████████████