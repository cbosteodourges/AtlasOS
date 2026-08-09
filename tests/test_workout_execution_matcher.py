"""Tests du rapprochement entre séance Atlas et activité réelle."""

import unittest
from datetime import date, datetime, timezone

from src.performance import (
    DetailedSessionAnalysis,
    LongitudinalActivity,
    SessionBlock,
)
from src.training import (
    AdaptiveWorkout,
    AtlasWorkoutExecutionMatcher,
    BlockType,
    IntensityTarget,
    TrainingBlock,
    WorkoutType,
)


class AtlasWorkoutExecutionMatcherTests(unittest.TestCase):
    """Valide le pont entre calendrier et activité Garmin."""

    def test_matches_real_activity_to_planned_workout(
        self,
    ) -> None:
        planned = AdaptiveWorkout(
            workout_id="semi-lille-w01-z2",
            workout_date=date(2026, 8, 9),
            workout_type=WorkoutType.ENDURANCE_Z2,
            title="Endurance fondamentale Z2",
            objective="Développer l'endurance aérobie",
            blocks=[
                TrainingBlock(
                    name="Corps de séance",
                    block_type=BlockType.CONTINUOUS,
                    duration_minutes=45,
                    target=IntensityTarget(
                        zone=2,
                        speed_min_kmh=9.5,
                        speed_max_kmh=10.8,
                        heart_rate_min_bpm=125,
                        heart_rate_max_bpm=145,
                    ),
                ),
            ],
            planned_duration_minutes=45,
            planned_distance_km=7.5,
        )
        activity = LongitudinalActivity(
            atlas_id="garmin-activity-001",
            start_time=datetime(
                2026,
                8,
                9,
                17,
                0,
                tzinfo=timezone.utc,
            ),
            activity_type="running",
            distance_km=7.4,
            duration_minutes=45.5,
            average_heart_rate_bpm=136,
            average_speed_kmh=9.76,
            elevation_gain_m=35,
            title="Course à pied",
            data_quality_score=94,
        )
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=[
                SessionBlock(
                    block_index=0,
                    block_type="z2",
                    start_offset_seconds=0,
                    end_offset_seconds=2730,
                    duration_seconds=2730,
                    distance_meters=7400,
                    average_speed_kmh=9.76,
                    average_heart_rate_bpm=136,
                    physiological_load_score=42,
                    biomechanical_load_score=36,
                    confidence_score=94,
                ),
            ],
            physiological_load_score=42,
            biomechanical_load_score=36,
            analysis_confidence_score=94,
        )

        result = AtlasWorkoutExecutionMatcher().match(
            planned,
            activity,
            analysis,
        )

        self.assertTrue(result.matched)
        self.assertGreaterEqual(
            result.match_confidence_score,
            95,
        )
        self.assertEqual(
            result.workout_id,
            planned.workout_id,
        )
        self.assertEqual(
            result.activity_id,
            activity.atlas_id,
        )
        self.assertEqual(
            result.execution.workout_origin,
            "atlas",
        )
        self.assertEqual(
            result.target_compliance_score,
            100,
        )
        self.assertEqual(
            result.physiological_load_score,
            42,
        )
        self.assertEqual(
            result.biomechanical_load_score,
            36,
        )


if __name__ == "__main__":
    unittest.main()