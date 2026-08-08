"""
ATLAS OS
Fusion des données connectées et déclaratives.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Optional

from .physiology_engine import PhysiologyInput


@dataclass(slots=True)
class RecoveryFusionResult:
    """Entrée physiologique fusionnée et provenance des champs."""

    physiology_input: PhysiologyInput
    mode: str
    sources_by_field: dict[str, str]
    conflicts: list[str]


class RecoveryFusionEngine:
    """Fusionne capteurs et bilan manuel sans inventer de valeur."""

    MANUAL_PRIORITY_FIELDS = {
        "stress_0_10",
        "subjective_fatigue_0_10",
        "muscle_soreness_0_10",
        "pain_0_10",
        "illness_symptoms",
    }

    SENSOR_PRIORITY_FIELDS = {
        "hrv_ms",
        "hrv_baseline_ms",
        "resting_hr_bpm",
        "resting_hr_baseline_bpm",
        "sleep_hours",
        "sleep_quality_0_100",
        "acute_load_7d",
        "chronic_load_28d",
        "vo2max",
        "vo2max_baseline",
    }

    def fuse(
        self,
        *,
        sensor_input: Optional[PhysiologyInput] = None,
        manual_input: Optional[PhysiologyInput] = None,
    ) -> RecoveryFusionResult:
        """Construit l’entrée la plus complète disponible."""
        if sensor_input is None and manual_input is None:
            raise ValueError(
                "Au moins une source de récupération est requise."
            )

        if sensor_input is not None and manual_input is not None:
            mode = "hybrid"
        elif sensor_input is not None:
            mode = "connected"
        else:
            mode = "manual"

        values: dict[str, Any] = {}
        sources: dict[str, str] = {}
        conflicts: list[str] = []

        for model_field in fields(PhysiologyInput):
            name = model_field.name

            if name == "notes":
                values[name], sources[name] = self._merge_notes(
                    sensor_input,
                    manual_input,
                )
                continue

            sensor_value = self._get(
                sensor_input,
                name,
            )
            manual_value = self._get(
                manual_input,
                name,
            )

            if self._different(
                sensor_value,
                manual_value,
            ):
                conflicts.append(
                    f"{name} diffère entre capteur "
                    "et déclaration manuelle."
                )

            if name in self.MANUAL_PRIORITY_FIELDS:
                value, source = self._prefer(
                    manual_value,
                    sensor_value,
                    "manual",
                    "sensor",
                )
            else:
                value, source = self._prefer(
                    sensor_value,
                    manual_value,
                    "sensor",
                    "manual",
                )

            if value is None:
                value = self._default_value(
                    model_field.default
                )
                source = "default"

            values[name] = value
            sources[name] = source

        return RecoveryFusionResult(
            physiology_input=PhysiologyInput(**values),
            mode=mode,
            sources_by_field=sources,
            conflicts=conflicts,
        )

    @staticmethod
    def _get(
        source: Optional[PhysiologyInput],
        name: str,
    ) -> Any:
        if source is None:
            return None
        return getattr(source, name)

    @staticmethod
    def _prefer(
        primary: Any,
        secondary: Any,
        primary_source: str,
        secondary_source: str,
    ) -> tuple[Any, str]:
        if primary is not None:
            return primary, primary_source
        if secondary is not None:
            return secondary, secondary_source
        return None, "missing"

    @staticmethod
    def _different(
        sensor_value: Any,
        manual_value: Any,
    ) -> bool:
        if sensor_value is None or manual_value is None:
            return False
        if isinstance(sensor_value, bool):
            return sensor_value != manual_value
        if isinstance(sensor_value, (int, float)):
            return abs(
                float(sensor_value)
                - float(manual_value)
            ) > 0.01
        return sensor_value != manual_value

    @staticmethod
    def _merge_notes(
        sensor_input: Optional[PhysiologyInput],
        manual_input: Optional[PhysiologyInput],
    ) -> tuple[str, str]:
        notes = []

        for source in (
            sensor_input,
            manual_input,
        ):
            if source is not None and source.notes.strip():
                if source.notes.strip() not in notes:
                    notes.append(source.notes.strip())

        if not notes:
            return "", "default"
        if len(notes) == 2:
            return " ".join(notes), "hybrid"
        if (
            manual_input is not None
            and manual_input.notes.strip()
        ):
            return notes[0], "manual"
        return notes[0], "sensor"

    @staticmethod
    def _default_value(default: Any) -> Any:
        if default is not None:
            return default
        return None