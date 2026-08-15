"""Tests de sélection progressive des séances historiques."""

import unittest

from src.training.historical_workout_pattern_analyzer import (
    HistoricalWorkoutPattern,
)
from src.training.historical_workout_progression_selector import (
    HistoricalWorkoutProgressionSelector,
)


def pattern(
    pattern_type: str,
    source_id: str,
    *,
    repetitions: int = 0,
    distance: int | None = None,
    groups: list[int] | None = None,
) -> HistoricalWorkoutPattern:
    return HistoricalWorkoutPattern(
        pattern_type=pattern_type,
        source_activity_id=source_id,
        source_date="2025-08-01",
        reference_event_title="Semi réussi",
        reference_outcome="successful",
        days_before_event=30,
        comparable_distance=True,
        repetitions=repetitions,
        work_distance_meters=distance,
        group_distances_meters=groups or [],
        confidence_score=90,
    )


class HistoricalWorkoutProgressionSelectorTests(
    unittest.TestCase
):
    """Valide une progression variée issue des réussites."""

    def test_builds_varied_half_marathon_progression(
        self,
    ) -> None:
        patterns = [
            pattern(
                "short_intervals",
                "short-8",
                repetitions=8,
                distance=400,
            ),
            pattern(
                "short_intervals",
                "short-10",
                repetitions=10,
                distance=400,
            ),
            pattern(
                "threshold_intervals",
                "threshold-4",
                repetitions=4,
                distance=1000,
            ),
            pattern(
                "threshold_intervals",
                "threshold-6",
                repetitions=6,
                distance=1000,
            ),
            pattern(
                "short_intervals",
                "mixed",
                repetitions=4,
                distance=400,
            ),
            pattern(
                "threshold_intervals",
                "mixed",
                repetitions=4,
                distance=1000,
            ),
            pattern(
                "long_race_specific",
                "long",
                repetitions=3,
                groups=[4000, 3000, 3000],
            ),
        ]

        result = (
            HistoricalWorkoutProgressionSelector()
            .build(patterns)
        )

        self.assertEqual(
            [item.kind for item in result.base],
            ["short_intervals"],
        )
        self.assertEqual(
            [item.kind for item in result.development],
            [
                "threshold_intervals",
                "short_intervals",
            ],
        )
        self.assertEqual(
            [item.kind for item in result.specific],
            [
                "mixed_intervals",
                "threshold_intervals",
                "short_intervals",
                "long_race_specific",
            ],
        )
        self.assertEqual(
            result.specific[0].repetitions,
            4,
        )
        self.assertEqual(
            result.specific[1].repetitions,
            6,
        )
        self.assertEqual(
            result.specific[-1].group_distances_meters,
            [4000, 3000, 3000],
        )

    def test_rejects_failed_or_non_comparable_patterns(
        self,
    ) -> None:
        failed = pattern(
            "short_intervals",
            "failed",
            repetitions=8,
            distance=400,
        )
        failed.reference_outcome = "failed"
        failed.comparable_distance = True

        result = (
            HistoricalWorkoutProgressionSelector()
            .build([failed])
        )

        self.assertFalse(result.available)
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()