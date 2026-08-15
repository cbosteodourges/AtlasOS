"""Tests de l'apprentissage des structures d'entraînement passées."""

import unittest

from src.training.historical_workout_pattern_analyzer import (
    HistoricalWorkoutPatternAnalyzer,
)


def block(
    block_type: str,
    distance_meters: int,
    speed_kmh: float,
    *,
    duration_seconds: int = 100,
) -> dict:
    return {
        "block_type": block_type,
        "distance_meters": distance_meters,
        "duration_seconds": duration_seconds,
        "average_speed_kmh": speed_kmh,
        "confidence_score": 90,
    }


class HistoricalWorkoutPatternAnalyzerTests(unittest.TestCase):
    """Valide l'extraction des séances réellement effectuées."""

    def setUp(self) -> None:
        self.activities = [
            {
                "activity_id": "eight-400",
                "start_time": "2025-09-04T19:56:05+02:00",
                "sport": "running",
                "confidence_score": 95,
            },
            {
                "activity_id": "four-1000",
                "start_time": "2025-08-01T19:10:04+02:00",
                "sport": "running",
                "confidence_score": 95,
            },
            {
                "activity_id": "long-specific",
                "start_time": "2025-09-06T18:36:35+02:00",
                "sport": "running",
                "confidence_score": 95,
            },
        ]
        self.analyses = [
            {
                "activity_id": "eight-400",
                "blocks": [
                    item
                    for _ in range(8)
                    for item in (
                        block("vma", 400, 14.0),
                        block(
                            "recovery",
                            100,
                            7.0,
                            duration_seconds=55,
                        ),
                    )
                ],
            },
            {
                "activity_id": "four-1000",
                "blocks": [
                    item
                    for _ in range(4)
                    for item in (
                        block("sv2", 1000, 13.1, duration_seconds=275),
                        block(
                            "recovery",
                            160,
                            6.0,
                            duration_seconds=95,
                        ),
                    )
                ],
            },
            {
                "activity_id": "long-specific",
                "blocks": (
                    [block("z3", 1000, 11.4, duration_seconds=316)] * 3
                    + [block("z2", 1000, 9.5, duration_seconds=379)]
                    + [block("z3", 1000, 11.5, duration_seconds=313)] * 3
                ),
            },
        ]

    def test_extracts_short_threshold_and_long_specific_patterns(
        self,
    ) -> None:
        result = HistoricalWorkoutPatternAnalyzer().analyze(
            {
                "activities": self.activities,
                "analyses": self.analyses,
            },
            vma_kmh=14.0,
            goal_speed_kmh=11.61,
            goal_distance_km=21.1,
            competition_payload={
                "analyses": [
                    {
                        "event": {
                            "event_date": (
                                "2025-09-21T00:00:00+02:00"
                            ),
                            "title": "Semi réussi",
                            "distance_km": 21.31,
                            "outcome": "successful",
                        }
                    }
                ]
            },
        )

        by_type = {
            pattern.pattern_type: pattern
            for pattern in result.patterns
        }

        self.assertEqual(
            by_type["short_intervals"].repetitions,
            8,
        )
        self.assertEqual(
            by_type["short_intervals"].work_distance_meters,
            400,
        )
        self.assertEqual(
            by_type["threshold_intervals"].repetitions,
            4,
        )
        self.assertEqual(
            by_type["threshold_intervals"].work_distance_meters,
            1000,
        )
        self.assertEqual(
            by_type["long_race_specific"].group_distances_meters,
            [3000, 3000],
        )
        self.assertEqual(result.activities_analyzed, 3)
        self.assertEqual(
            by_type["short_intervals"].reference_event_title,
            "Semi réussi",
        )
        self.assertEqual(
            by_type["short_intervals"].reference_outcome,
            "successful",
        )
        self.assertEqual(
            by_type["short_intervals"].days_before_event,
            17,
        )
        self.assertTrue(
            by_type["short_intervals"].comparable_distance
        )

    def test_ignores_non_running_and_low_confidence_data(
        self,
    ) -> None:
        activities = [
            {
                "activity_id": "cycling",
                "start_time": "2025-08-01T10:00:00+02:00",
                "sport": "cycling",
                "confidence_score": 95,
            },
            {
                "activity_id": "uncertain",
                "start_time": "2025-08-02T10:00:00+02:00",
                "sport": "running",
                "confidence_score": 40,
            },
        ]
        analyses = [
            {
                "activity_id": item["activity_id"],
                "blocks": [
                    block("vma", 400, 14.0)
                    for _ in range(8)
                ],
            }
            for item in activities
        ]

        result = HistoricalWorkoutPatternAnalyzer().analyze(
            {
                "activities": activities,
                "analyses": analyses,
            },
            vma_kmh=14.0,
            goal_speed_kmh=11.61,
        )

        self.assertEqual(result.patterns, [])
        self.assertEqual(result.activities_analyzed, 0)


if __name__ == "__main__":
    unittest.main()