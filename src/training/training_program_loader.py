"""
ATLAS OS
Chargement d'un programme adaptatif exporté en JSON.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .session_models import (
    AdaptiveWorkout,
    BlockType,
    ExpectedTrainingResponse,
    IntensityTarget,
    TrainingBlock,
    WorkoutPriority,
    WorkoutType,
)


class TrainingProgramLoader:
    """Reconstruit les séances Atlas depuis un export JSON."""

    def load(
        self,
        program_path: str | Path,
    ) -> list[AdaptiveWorkout]:
        """Charge et valide toutes les séances du programme."""
        source = Path(program_path)
        if not source.exists():
            raise FileNotFoundError(
                f"Programme Atlas introuvable : {source}"
            )

        with source.open("r", encoding="utf-8") as input_file:
            payload = json.load(input_file)

        return self.from_payload(payload)

    def from_payload(
        self,
        payload: dict[str, Any],
    ) -> list[AdaptiveWorkout]:
        """Reconstruit les séances depuis un dictionnaire."""
        weeks = payload.get("weeks", [])
        if not isinstance(weeks, list):
            raise ValueError(
                "Le champ weeks du programme doit être une liste."
            )

        workouts: list[AdaptiveWorkout] = []
        identifiers: set[str] = set()

        for week in weeks:
            for raw_workout in week.get("workouts", []):
                workout = self._workout(raw_workout)
                if workout.workout_id in identifiers:
                    raise ValueError(
                        "Identifiant de séance dupliqué : "
                        f"{workout.workout_id}"
                    )

                workout.validate()
                identifiers.add(workout.workout_id)
                workouts.append(workout)

        return sorted(
            workouts,
            key=lambda item: (
                item.workout_date,
                item.workout_id,
            ),
        )

    def candidates_for_activity(
        self,
        workouts: list[AdaptiveWorkout],
        *,
        activity_date: date,
        sport: str,
        maximum_difference_days: int = 2,
    ) -> list[AdaptiveWorkout]:
        """Retourne les séances susceptibles de correspondre."""
        normalized_sport = sport.strip().lower()

        candidates = [
            workout
            for workout in workouts
            if abs(
                (
                    workout.workout_date
                    - activity_date
                ).days
            )
            <= maximum_difference_days
            and self._same_sport(
                workout.sport,
                normalized_sport,
            )
        ]

        return sorted(
            candidates,
            key=lambda item: (
                abs(
                    (
                        item.workout_date
                        - activity_date
                    ).days
                ),
                item.workout_date,
                item.workout_id,
            ),
        )

    def _workout(
        self,
        value: dict[str, Any],
    ) -> AdaptiveWorkout:
        expected = value.get("expected_response")

        return AdaptiveWorkout(
            workout_id=str(value["workout_id"]),
            workout_date=date.fromisoformat(
                str(value["workout_date"])
            ),
            workout_type=WorkoutType(
                value["workout_type"]
            ),
            title=str(value["title"]),
            objective=str(value["objective"]),
            blocks=[
                self._block(block)
                for block in value.get("blocks", [])
            ],
            sport=str(value.get("sport", "running")),
            priority=WorkoutPriority(
                value.get(
                    "priority",
                    WorkoutPriority.SUPPORT.value,
                )
            ),
            planned_duration_minutes=value.get(
                "planned_duration_minutes"
            ),
            planned_distance_km=value.get(
                "planned_distance_km"
            ),
            expected_response=(
                ExpectedTrainingResponse(
                    physiological_load_0_100=int(
                        expected[
                            "physiological_load_0_100"
                        ]
                    ),
                    biomechanical_load_0_100=int(
                        expected[
                            "biomechanical_load_0_100"
                        ]
                    ),
                    recovery_min_hours=int(
                        expected["recovery_min_hours"]
                    ),
                    recovery_max_hours=int(
                        expected["recovery_max_hours"]
                    ),
                    sensitive_structures=list(
                        expected.get(
                            "sensitive_structures",
                            [],
                        )
                    ),
                )
                if expected is not None
                else None
            ),
            movable=bool(value.get("movable", True)),
            maximum_shift_days=int(
                value.get("maximum_shift_days", 2)
            ),
            replacement_types=[
                WorkoutType(item)
                for item in value.get(
                    "replacement_types",
                    [],
                )
            ],
            coach_notes=list(
                value.get("coach_notes", [])
            ),
        )

    @staticmethod
    def _block(
        value: dict[str, Any],
    ) -> TrainingBlock:
        target = value.get("target") or {}

        return TrainingBlock(
            name=str(value["name"]),
            block_type=BlockType(value["block_type"]),
            repetitions=int(value.get("repetitions", 1)),
            duration_minutes=value.get(
                "duration_minutes"
            ),
            distance_meters=value.get(
                "distance_meters"
            ),
            recovery_minutes=value.get(
                "recovery_minutes"
            ),
            target=IntensityTarget(
                zone=target.get("zone"),
                pace_min_per_km=target.get(
                    "pace_min_per_km"
                ),
                pace_max_per_km=target.get(
                    "pace_max_per_km"
                ),
                heart_rate_min_bpm=target.get(
                    "heart_rate_min_bpm"
                ),
                heart_rate_max_bpm=target.get(
                    "heart_rate_max_bpm"
                ),
                speed_min_kmh=target.get(
                    "speed_min_kmh"
                ),
                speed_max_kmh=target.get(
                    "speed_max_kmh"
                ),
                power_min_watts=target.get(
                    "power_min_watts"
                ),
                power_max_watts=target.get(
                    "power_max_watts"
                ),
                rpe_0_10=target.get("rpe_0_10"),
                gradient_min_percent=target.get(
                    "gradient_min_percent"
                ),
                gradient_max_percent=target.get(
                    "gradient_max_percent"
                ),
                intensity_pattern=str(
                    target.get(
                        "intensity_pattern",
                        "constant",
                    )
                ),
                transition_seconds=target.get(
                    "transition_seconds"
                ),
            ),
            instructions=str(
                value.get("instructions", "")
            ),
        )

    @staticmethod
    def _same_sport(
        planned: str,
        actual: str,
    ) -> bool:
        running_aliases = {
            "running",
            "run",
            "course",
            "course à pied",
        }
        left = planned.strip().lower()
        right = actual.strip().lower()

        return (
            left == right
            or (
                left in running_aliases
                and right in running_aliases
            )
        )