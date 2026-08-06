"""
ATLAS OS
Adaptation des activités normalisées vers Performance Intelligence.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from src.connectors import NormalizedActivity

from .longitudinal_models import (
    EnergyMetrics,
    EnvironmentMetrics,
    LongitudinalActivity,
    RecoveryMetrics,
    RunningDynamics,
)
from .models import TrainingActivity


class LongitudinalActivityAdapter:
    """Transforme une activité commune en activité longitudinale."""

    def adapt(
        self,
        activity: NormalizedActivity,
    ) -> LongitudinalActivity:
        metadata = activity.raw_metadata

        dynamics = RunningDynamics(
            average_cadence_spm=self._number(
                metadata.get("average_cadence")
            ),
            maximum_cadence_spm=self._number(
                metadata.get("maximum_cadence")
            ),
            average_stride_length_m=self._number(
                metadata.get("average_stride_length")
            ),
            average_vertical_ratio_percent=self._number(
                metadata.get("average_vertical_ratio")
            ),
            average_vertical_oscillation_cm=self._number(
                metadata.get(
                    "average_vertical_oscillation"
                )
            ),
            average_ground_contact_time_ms=self._number(
                metadata.get(
                    "average_ground_contact_time"
                )
            ),
            average_power_watts=self._number(
                metadata.get("average_power")
            ),
            maximum_power_watts=self._number(
                metadata.get("maximum_power")
            ),
            normalized_power_watts=self._number(
                metadata.get("normalized_power")
            ),
        )

        environment = EnvironmentMetrics(
            average_temperature_c=self._number(
                metadata.get("average_temperature")
            ),
            minimum_temperature_c=self._number(
                metadata.get("minimum_temperature")
            ),
            maximum_temperature_c=self._number(
                metadata.get("maximum_temperature")
            ),
            minimum_altitude_m=self._number(
                metadata.get("minimum_altitude")
            ),
            maximum_altitude_m=self._number(
                metadata.get("maximum_altitude")
            ),
        )

        recovery = RecoveryMetrics(
             perceived_effort_1_to_10=self._number(
                metadata.get("perceived_effort")
            ),
            feeling_score_0_to_100=self._number(
                metadata.get("feeling_score")
            ),
            feeling_label=(
                str(metadata.get("feeling_label"))
                if metadata.get("feeling_label")
                is not None
                else None
            ),
            aerobic_training_effect=self._number(
                metadata.get(
                    "aerobic_training_effect"
                )
            ),
            anaerobic_training_effect=self._number(
                metadata.get(
                    "anaerobic_training_effect"
                )
            ),
            body_battery_impact=self._number(
                metadata.get(
                    "body_battery_consumption"
                )
            ),
            moderate_intensity_minutes=self._number(
                metadata.get(
                    "moderate_intensity_minutes"
                )
            ),
            vigorous_intensity_minutes=self._number(
                metadata.get(
                    "vigorous_intensity_minutes"
                )
            ),
            total_intensity_minutes=self._number(
                metadata.get(
                    "total_intensity_minutes"
                )
            ),
            average_respiration_rate=self._number(
                metadata.get(
                    "average_respiration_rate"
                )
            ),
            minimum_respiration_rate=self._number(
                metadata.get(
                    "minimum_respiration_rate"
                )
            ),
            maximum_respiration_rate=self._number(
                metadata.get(
                    "maximum_respiration_rate"
                )
            ),
        )

        energy = EnergyMetrics(
            active_calories_kcal=self._number(
                metadata.get("active_calories")
            ),
            total_calories_kcal=activity.calories_kcal,
            estimated_sweat_loss_ml=self._number(
                metadata.get(
                    "estimated_sweat_loss"
                )
            ),
            carbohydrate_intake_g=self._number(
                metadata.get(
                    "carbohydrate_intake"
                )
            ),
            fluid_intake_ml=self._number(
                metadata.get("fluid_intake")
            ),
        )

        return LongitudinalActivity(
            atlas_id=activity.atlas_id,
            start_time=self._date(activity.start_time),
            activity_type=activity.activity_type,
            distance_km=(
                activity.distance_meters or 0
            ) / 1000,
            duration_minutes=(
                activity.duration_seconds / 60
            ),
            average_heart_rate_bpm=(
                activity.average_heart_rate_bpm
            ),
            maximum_heart_rate_bpm=(
                activity.maximum_heart_rate_bpm
            ),
            average_speed_kmh=(
                activity.average_speed_mps * 3.6
                if activity.average_speed_mps
                is not None
                else None
            ),
            elevation_gain_m=activity.elevation_gain_m,
            training_load=activity.training_load,
            dynamics=dynamics,
            environment=environment,
            recovery=recovery,
            energy=energy,
            samples=list(activity.samples),
            laps=list(metadata.get("laps") or []),
            time_in_zones=list(
                metadata.get("time_in_zones") or []
            ),
            workout=list(metadata.get("workout") or []),
            workout_steps=list(
                metadata.get("workout_steps") or []
            ),
            events=list(metadata.get("events") or []),
            source=activity.provider,
            title=str(metadata.get("title") or ""),
            data_quality_score=self._quality_score(
                activity,
                dynamics,
                environment,
                recovery,
            ),
        )

    @staticmethod
    def _date(value: str) -> datetime:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    @staticmethod
    def _number(
        value: Any,
    ) -> Optional[float]:
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _quality_score(
        activity: NormalizedActivity,
        dynamics: RunningDynamics,
        environment: EnvironmentMetrics,
        recovery: RecoveryMetrics,
    ) -> int:
        available_values = [
            activity.distance_meters,
            activity.duration_seconds,
            activity.average_heart_rate_bpm,
            activity.maximum_heart_rate_bpm,
            activity.average_speed_mps,
            activity.elevation_gain_m,
            activity.calories_kcal,
            dynamics.average_cadence_spm,
            dynamics.average_stride_length_m,
            dynamics.average_vertical_ratio_percent,
            dynamics.average_vertical_oscillation_cm,
            dynamics.average_ground_contact_time_ms,
            environment.minimum_temperature_c,
            environment.maximum_temperature_c,
            recovery.aerobic_training_effect,
            recovery.body_battery_impact,
        ]

        available_count = sum(
            value is not None
            for value in available_values
        )

        return round(
            available_count
            / len(available_values)
            * 100
        )

class TrainingActivityAdapter:
    """Adapte le mod?le longitudinal au g?n?rateur historique."""

    def adapt(
        self,
        activity: LongitudinalActivity,
    ) -> TrainingActivity:
        """Convertit une activit? longitudinale."""
        perceived_effort = (
            round(
                activity.recovery
                .perceived_effort_1_to_10
            )
            if (
                activity.recovery
                .perceived_effort_1_to_10
                is not None
            )
            else None
        )

        return TrainingActivity(
            activity_date=activity.start_time.date(),
            activity_type=activity.activity_type,
            distance_km=activity.distance_km,
            duration_minutes=max(
                0,
                round(activity.duration_minutes),
            ),
            average_heart_rate=self._integer(
                activity.average_heart_rate_bpm
            ),
            maximum_heart_rate=self._integer(
                activity.maximum_heart_rate_bpm
            ),
            perceived_exertion=perceived_effort,
            completed=True,
            notes=activity.title,
        )

    @staticmethod
    def _integer(
        value: Optional[float],
    ) -> Optional[int]:
        if value is None:
            return None

        return round(value)

