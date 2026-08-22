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

    def test_penalizes_shortened_recoveries(self) -> None:
        planned = AdaptiveWorkout(
            workout_id="threshold-recovery-test",
            workout_date=date(2026, 8, 9),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="Seuil SV2",
            objective="Travail au seuil",
            blocks=[TrainingBlock(
                name="3 × 8 min au SV2",
                block_type=BlockType.WORK,
                repetitions=3,
                duration_minutes=8,
                recovery_minutes=2,
                target=IntensityTarget(zone=4, speed_min_kmh=12, speed_max_kmh=12.9),
            )],
            planned_duration_minutes=40,
        )
        activity = LongitudinalActivity(
            atlas_id="garmin-short-recovery",
            start_time=datetime(2026, 8, 9, 17, tzinfo=timezone.utc),
            activity_type="running",
            distance_km=8,
            duration_minutes=40,
            average_speed_kmh=12.4,
        )
        blocks = [
            SessionBlock(1, "sv2", 0, 480, 480, 1650, average_speed_kmh=12.4),
            SessionBlock(2, "recovery", 480, 520, 40, 80),
            SessionBlock(3, "sv2", 520, 1000, 480, 1650, average_speed_kmh=12.4),
            SessionBlock(4, "recovery", 1000, 1040, 40, 80),
            SessionBlock(5, "sv2", 1040, 1520, 480, 1650, average_speed_kmh=12.4),
        ]
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=blocks,
            dominant_work_type="sv2",
            session_type="threshold",
            recovery_duration_seconds=80,
        )

        result = AtlasWorkoutExecutionMatcher().match(planned, activity, analysis)

        self.assertLess(result.execution.recovery_compliance_score, 50)
        self.assertTrue(any("écourtées" in reason for reason in result.reasons))

    def test_hybrid_counts_only_repeated_work_blocks(self) -> None:
        planned = AdaptiveWorkout(
            workout_id="hybrid-3x6",
            workout_date=date(2026, 8, 22),
            workout_type=WorkoutType.LONG_RUN,
            title="Sortie longue hybride · 3 × 6 min sous SV2",
            objective="Résistance à la fatigue",
            blocks=[
                TrainingBlock(
                    name="Endurance avant les blocs",
                    block_type=BlockType.CONTINUOUS,
                    repetitions=1,
                    duration_minutes=23,
                    target=IntensityTarget(zone=2),
                ),
                TrainingBlock(
                    name="3 × 6 min sous SV2",
                    block_type=BlockType.WORK,
                    repetitions=3,
                    duration_minutes=6,
                    recovery_minutes=2,
                    target=IntensityTarget(
                        zone=3,
                        speed_min_kmh=11.9,
                        speed_max_kmh=12.5,
                    ),
                ),
            ],
            planned_duration_minutes=70,
        )
        activity = LongitudinalActivity(
            atlas_id="garmin-hybrid-3x6",
            start_time=datetime(
                2026, 8, 22, 17, tzinfo=timezone.utc
            ),
            activity_type="running",
            distance_km=10,
            duration_minutes=70,
            average_speed_kmh=10,
        )
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=[
                SessionBlock(1, "z2", 0, 900, 900, 2400),
                SessionBlock(2, "z3", 900, 1260, 360, 1200),
                SessionBlock(3, "recovery", 1260, 1380, 120, 220),
                SessionBlock(4, "z3", 1380, 1740, 360, 1200),
                SessionBlock(5, "recovery", 1740, 1860, 120, 220),
                SessionBlock(6, "z3", 1860, 2220, 360, 1200),
            ],
            dominant_work_type="z3",
            session_type="long_run",
            recovery_duration_seconds=240,
        )

        result = AtlasWorkoutExecutionMatcher().match(
            planned, activity, analysis
        )

        self.assertEqual(result.execution.planned_repetition_count, 3)
        self.assertEqual(result.execution.completed_repetition_count, 3)


if __name__ == "__main__":
    unittest.main()
