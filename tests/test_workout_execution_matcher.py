"""Tests du rapprochement entre séance Atlas et activité réelle."""

import unittest
from datetime import date, datetime, timedelta, timezone

from src.connectors.activity_schema import ActivitySample
from src.performance import (
    DetailedSessionAnalysis,
    LongitudinalActivity,
    SessionBlock,
    WorkoutExecutionSummary,
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

    def test_aligns_heterogeneous_vo2_pyramid_and_ignores_false_fragment(self) -> None:
        target = IntensityTarget(
            zone=4,
            speed_min_kmh=13.3,
            speed_max_kmh=14.0,
        )
        planned = AdaptiveWorkout(
            workout_id="vo2-pyramid",
            workout_date=date(2026, 9, 1),
            workout_type=WorkoutType.TRIANGULAR_VO2,
            title="VO2 pyramidal",
            objective="Varier le temps de soutien",
            blocks=[
                TrainingBlock("2 x 3", BlockType.WORK, 2, 3, recovery_minutes=1.5, target=target),
                TrainingBlock("2 x 2", BlockType.WORK, 2, 2, recovery_minutes=1.5, target=target),
                TrainingBlock(
                    "1 à 2 x 1:30", BlockType.WORK, 1, 1.5,
                    recovery_minutes=1.5, target=target,
                    instructions="La seconde répétition est facultative.",
                ),
            ],
            planned_duration_minutes=50,
        )
        start = datetime(2026, 9, 1, 18, tzinfo=timezone.utc)
        samples = [
            ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=9.5 / 3.6,
            )
            for offset in range(0, 800, 10)
        ]
        for interval_start, duration, speed in (
            (910, 180, 13.61),
            (1179, 180, 13.72),
            (1459, 100, 13.64),
            (1654, 115, 14.30),
            (1869, 85, 14.62),
            (2049, 80, 14.63),
        ):
            samples.append(ActivitySample(
                timestamp=start + timedelta(seconds=interval_start - 10),
                speed_mps=9.0 / 3.6,
            ))
            for offset in range(0, duration + 1, 10):
                samples.append(ActivitySample(
                    timestamp=start + timedelta(seconds=interval_start + offset),
                    speed_mps=speed / 3.6,
                    heart_rate_bpm=145,
                ))
            samples.append(ActivitySample(
                timestamp=start + timedelta(seconds=interval_start + duration + 10),
                speed_mps=8.0 / 3.6,
            ))
        activity = LongitudinalActivity(
            atlas_id="health-connect-pyramid",
            start_time=start,
            activity_type="running",
            distance_km=7.5,
            duration_minutes=40,
            average_speed_kmh=11.2,
            samples=samples,
        )
        blocks = [
            SessionBlock(1, "z3", 0, 100, 100, 290, average_speed_kmh=10.43),
            SessionBlock(2, "recovery", 100, 200, 100, 180),
            SessionBlock(3, "vma", 200, 380, 180, 681, average_speed_kmh=13.62),
            SessionBlock(4, "recovery", 380, 460, 80, 178),
            SessionBlock(5, "vma", 460, 640, 180, 685, average_speed_kmh=13.78),
            SessionBlock(6, "recovery", 640, 720, 80, 174),
            SessionBlock(7, "vma", 720, 840, 120, 455, average_speed_kmh=13.65),
            SessionBlock(8, "recovery", 840, 925, 85, 160),
            SessionBlock(9, "vma", 925, 1045, 120, 458, average_speed_kmh=13.74),
            SessionBlock(10, "recovery", 1045, 1128, 83, 155),
            SessionBlock(11, "vma", 1128, 1218, 90, 344, average_speed_kmh=13.76),
        ]
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=blocks,
            dominant_work_type="vma",
            session_type="vma",
            recovery_duration_seconds=428,
        )

        result = AtlasWorkoutExecutionMatcher().match(planned, activity, analysis)

        self.assertEqual(result.execution.planned_repetition_count, 5)
        self.assertEqual(result.execution.completed_repetition_count, 6)
        self.assertEqual(
            [round(item["duration_seconds"]) for item in result.execution.interval_details],
            [180, 180, 120, 120, 90, 90],
        )
        self.assertTrue(all(
            item["start_seconds"] < item["end_seconds"]
            for item in result.execution.interval_details
        ))
        self.assertTrue(all(
            item["recovery_distance_meters"] is not None
            for item in result.execution.interval_details[:-1]
        ))
        self.assertGreaterEqual(result.target_compliance_score, 75)
        self.assertGreaterEqual(result.execution.recovery_compliance_score, 85)

        for block in planned.blocks:
            block.target.speed_min_kmh = None
            block.target.speed_max_kmh = None
        inferred_groups = AtlasWorkoutExecutionMatcher._raw_speed_interval_groups(
            AtlasWorkoutExecutionMatcher._planned_intervals(planned),
            activity,
        )
        self.assertEqual(len(inferred_groups), 6)

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
        self.assertEqual(result.target_compliance_score, 100)

    def test_easy_running_after_threshold_does_not_lower_target_score(self) -> None:
        planned = AdaptiveWorkout(
            workout_id="threshold-with-family-cooldown",
            workout_date=date(2026, 8, 27),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="SV2 contrôlé · 3 à 4 × 1000 m",
            objective="Travail contrôlé au seuil",
            blocks=[TrainingBlock(
                name="3 × 1000 m",
                block_type=BlockType.WORK,
                repetitions=3,
                distance_meters=1000,
                recovery_minutes=1.75,
                target=IntensityTarget(
                    zone=4,
                    speed_min_kmh=12.4,
                    speed_max_kmh=13.1,
                ),
            )],
            planned_duration_minutes=50,
        )
        activity = LongitudinalActivity(
            atlas_id="garmin-threshold-family-cooldown",
            start_time=datetime(2026, 8, 27, 20, tzinfo=timezone.utc),
            activity_type="running",
            distance_km=9,
            duration_minutes=58,
            average_speed_kmh=9.3,
        )
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=[
                SessionBlock(1, "z3", 0, 280, 280, 1000, average_speed_kmh=12.86),
                SessionBlock(2, "recovery", 280, 385, 105, 180),
                SessionBlock(3, "sv2", 385, 665, 280, 1000, average_speed_kmh=12.86),
                SessionBlock(4, "recovery", 665, 770, 105, 180),
                SessionBlock(5, "z3", 770, 1050, 280, 1000, average_speed_kmh=12.86),
                SessionBlock(6, "z2", 1050, 2130, 1080, 3000, average_speed_kmh=10),
            ],
            dominant_work_type="sv2",
            session_type="threshold",
            recovery_duration_seconds=210,
        )

        result = AtlasWorkoutExecutionMatcher().match(planned, activity, analysis)

        self.assertEqual(result.target_compliance_score, 100)
        self.assertEqual(result.execution.completed_repetition_count, 3)

    def test_uses_structured_recovery_for_optional_repetition(self) -> None:
        planned = AdaptiveWorkout(
            workout_id="threshold-optional-fourth",
            workout_date=date(2026, 8, 27),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="SV2 contrôlé · 3 à 4 × 1000 m",
            objective="Travail contrôlé au seuil",
            blocks=[TrainingBlock(
                name="3 à 4 × 1000 m",
                block_type=BlockType.WORK,
                repetitions=3,
                distance_meters=1000,
                recovery_minutes=1.75,
                target=IntensityTarget(
                    zone=4,
                    speed_min_kmh=12.4,
                    speed_max_kmh=13.1,
                ),
            )],
            planned_duration_minutes=50,
        )
        activity = LongitudinalActivity(
            atlas_id="garmin-threshold-optional-fourth",
            start_time=datetime(2026, 8, 27, 20, tzinfo=timezone.utc),
            activity_type="running",
            distance_km=8,
            duration_minutes=52,
            average_speed_kmh=9.2,
            workout_steps=[{
                "message_index": 0,
                "duration_type": "distance",
                "duration_distance": 1000,
                "intensity": "active",
            }],
        )
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=[
                SessionBlock(1, "sv2", 0, 280, 280, 1000, average_speed_kmh=12.86),
                SessionBlock(2, "recovery", 280, 385, 105, 220),
                SessionBlock(3, "sv2", 385, 665, 280, 1000, average_speed_kmh=12.86),
                SessionBlock(4, "recovery", 665, 770, 105, 220),
                SessionBlock(5, "sv2", 770, 1050, 280, 1000, average_speed_kmh=12.86),
                SessionBlock(6, "recovery", 1050, 1155, 105, 220),
                SessionBlock(7, "sv2", 1155, 1435, 280, 1000, average_speed_kmh=12.86),
                SessionBlock(8, "recovery", 1435, 1554, 119, 250),
            ],
            dominant_work_type="sv2",
            session_type="threshold",
            recovery_duration_seconds=434,
            workout_execution=WorkoutExecutionSummary(
                planned_repetition_count=4,
                completed_repetition_count=4,
                recovery_compliance_score=100,
            ),
        )

        result = AtlasWorkoutExecutionMatcher().match(
            planned, activity, analysis
        )

        self.assertEqual(
            result.execution.recovery_compliance_score,
            100,
        )
        self.assertGreaterEqual(
            result.execution.execution_score,
            90,
        )


if __name__ == "__main__":
    unittest.main()
