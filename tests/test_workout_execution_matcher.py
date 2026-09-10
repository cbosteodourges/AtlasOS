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

    def test_detects_six_homogeneous_optional_three_minute_intervals(self) -> None:
        target = IntensityTarget(
            zone=5,
            speed_min_kmh=13.3,
            speed_max_kmh=14.3,
        )
        planned = AdaptiveWorkout(
            workout_id="vo2-six-by-three",
            workout_date=date(2026, 9, 8),
            workout_type=WorkoutType.VMA_LONG,
            title="Temps de soutien VO₂max · 4 à 6 × 3 min",
            objective="Développer le temps de soutien.",
            blocks=[TrainingBlock(
                "4 à 6 × 3 min",
                BlockType.WORK,
                4,
                3,
                recovery_minutes=2,
                target=target,
                instructions="Commencer par 4; plafond 6 si la dernière fraction reste propre.",
            )],
            planned_duration_minutes=54,
        )
        start = datetime(2026, 9, 8, 18, tzinfo=timezone.utc)
        samples = []
        for offset in range(0, 15 * 60, 10):
            samples.append(ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=10 / 3.6,
            ))
        cursor = 15 * 60
        for repetition in range(6):
            for offset in range(0, 181, 10):
                samples.append(ActivitySample(
                    timestamp=start + timedelta(seconds=cursor + offset),
                    speed_mps=(13.45 + repetition * .12) / 3.6,
                    heart_rate_bpm=145 + repetition * 2,
                ))
            cursor += 180
            if repetition < 5:
                for offset in range(10, 121, 10):
                    samples.append(ActivitySample(
                        timestamp=start + timedelta(seconds=cursor + offset),
                        speed_mps=6.5 / 3.6,
                        heart_rate_bpm=138,
                    ))
                cursor += 120
        activity = LongitudinalActivity(
            atlas_id="health-connect-six-by-three",
            start_time=start,
            activity_type="running",
            distance_km=8.7,
            duration_minutes=50,
            average_speed_kmh=10.4,
            samples=samples,
        )
        planned_intervals = AtlasWorkoutExecutionMatcher._planned_intervals(planned)
        groups = AtlasWorkoutExecutionMatcher._raw_speed_interval_groups(
            planned_intervals,
            activity,
        )

        self.assertEqual(len(planned_intervals), 6)
        self.assertEqual(
            [bool(item.get("optional")) for item in planned_intervals],
            [False, False, False, False, True, True],
        )
        self.assertEqual(len(groups), 6)
        self.assertEqual(
            [round(item["raw_recovery_seconds"]) for item in groups[:-1]],
            [120, 120, 120, 120, 120],
        )

    def test_detects_sparse_health_connect_intervals_sampled_every_30_seconds(
        self,
    ) -> None:
        target = IntensityTarget(zone=5, speed_min_kmh=13.3, speed_max_kmh=14.3)
        planned = AdaptiveWorkout(
            workout_id="sparse-four-by-three",
            workout_date=date(2026, 9, 8),
            workout_type=WorkoutType.VMA_LONG,
            title="VO₂max · 4 × 3 min",
            objective="Développer le temps de soutien.",
            blocks=[TrainingBlock(
                "4 × 3 min", BlockType.WORK, 4, 3,
                recovery_minutes=2, target=target,
            )],
            planned_duration_minutes=40,
        )
        start = datetime(2026, 9, 8, 18, tzinfo=timezone.utc)
        samples = []
        cursor = 10 * 60
        for repetition in range(4):
            for offset in range(0, 181, 30):
                samples.append(ActivitySample(
                    timestamp=start + timedelta(seconds=cursor + offset),
                    speed_mps=(13.5 + repetition * .1) / 3.6,
                    heart_rate_bpm=146 + repetition * 2,
                ))
            cursor += 180
            if repetition < 3:
                for offset in range(30, 121, 30):
                    samples.append(ActivitySample(
                        timestamp=start + timedelta(seconds=cursor + offset),
                        speed_mps=6.5 / 3.6,
                    ))
                cursor += 120

        groups = AtlasWorkoutExecutionMatcher._raw_speed_interval_groups(
            AtlasWorkoutExecutionMatcher._planned_intervals(planned),
            LongitudinalActivity(
                atlas_id="health-connect-sparse",
                start_time=start,
                activity_type="running",
                distance_km=7.0,
                duration_minutes=40,
                average_speed_kmh=10.5,
                samples=samples,
            ),
        )

        self.assertEqual(len(groups), 4)
        self.assertEqual([round(item["duration_seconds"]) for item in groups], [180] * 4)
        self.assertEqual(
            [round(item["raw_recovery_seconds"]) for item in groups[:-1]],
            [120, 120, 120],
        )

    def test_deduplicates_health_connect_points_and_tolerates_missing_heart_rate(
        self,
    ) -> None:
        planned = [{
            "duration_seconds": 180.0,
            "distance_meters": None,
            "recovery_minutes": 0.0,
            "planned": TrainingBlock(
                "3 min", BlockType.WORK, 1, 3,
                target=IntensityTarget(zone=5, speed_min_kmh=13.3),
            ),
        }]
        start = datetime(2026, 9, 8, 18, tzinfo=timezone.utc)
        samples = []
        for offset in range(0, 181, 10):
            point_time = start + timedelta(seconds=offset)
            samples.extend([
                ActivitySample(timestamp=point_time, speed_mps=13.8 / 3.6),
                ActivitySample(
                    timestamp=point_time,
                    speed_mps=13.8 / 3.6,
                    heart_rate_bpm=150 if offset in {0, 60, 120, 180} else None,
                ),
            ])

        groups = AtlasWorkoutExecutionMatcher._raw_speed_interval_groups(
            planned,
            LongitudinalActivity(
                atlas_id="health-connect-duplicates",
                start_time=start,
                activity_type="running",
                distance_km=1.0,
                duration_minutes=3,
                average_speed_kmh=13.8,
                samples=samples,
            ),
        )

        self.assertEqual(len(groups), 1)
        self.assertAlmostEqual(groups[0]["average_speed_kmh"], 13.8)
        self.assertEqual(groups[0]["average_heart_rate_bpm"], 150)

    def test_does_not_join_fast_samples_across_a_long_interruption(self) -> None:
        planned = [{
            "duration_seconds": 180.0,
            "distance_meters": None,
            "recovery_minutes": 0.0,
            "planned": TrainingBlock(
                "3 min", BlockType.WORK, 1, 3,
                target=IntensityTarget(zone=5, speed_min_kmh=13.3),
            ),
        }]
        start = datetime(2026, 9, 8, 18, tzinfo=timezone.utc)
        samples = [
            ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=13.8 / 3.6,
            )
            for offset in (*range(0, 91, 10), *range(390, 481, 10))
        ]

        groups = AtlasWorkoutExecutionMatcher._raw_speed_interval_groups(
            planned,
            LongitudinalActivity(
                atlas_id="health-connect-interrupted",
                start_time=start,
                activity_type="running",
                distance_km=1.4,
                duration_minutes=8,
                average_speed_kmh=10.5,
                samples=samples,
            ),
        )

        self.assertEqual(groups, [])

    def test_detects_five_threshold_blocks_without_absorbing_easy_running(self) -> None:
        target = IntensityTarget(
            zone=4,
            speed_min_kmh=12.2,
            speed_max_kmh=13.0,
        )
        planned = AdaptiveWorkout(
            workout_id="threshold-five-by-five",
            workout_date=date(2026, 9, 10),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="Seuil SV2 · 5 × 5 min",
            objective="Accumuler du temps au seuil.",
            blocks=[TrainingBlock(
                "5 × 5 min",
                BlockType.WORK,
                5,
                5,
                recovery_minutes=2,
                target=target,
            )],
            planned_duration_minutes=65,
        )
        start = datetime(2026, 9, 10, 18, tzinfo=timezone.utc)
        samples = []
        for offset in range(0, 18 * 60, 10):
            samples.append(ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=10.8 / 3.6,
            ))
        cursor = 18 * 60
        for repetition in range(5):
            for offset in range(0, 301, 10):
                samples.append(ActivitySample(
                    timestamp=start + timedelta(seconds=cursor + offset),
                    speed_mps=(12.35 + repetition * .1) / 3.6,
                    heart_rate_bpm=148 + repetition * 2,
                ))
            cursor += 300
            if repetition < 4:
                for offset in range(10, 121, 10):
                    samples.append(ActivitySample(
                        timestamp=start + timedelta(seconds=cursor + offset),
                        speed_mps=7.2 / 3.6,
                    ))
                cursor += 120
        for offset in range(10, 13 * 60, 10):
            samples.append(ActivitySample(
                timestamp=start + timedelta(seconds=cursor + offset),
                speed_mps=10.6 / 3.6,
            ))
        activity = LongitudinalActivity(
            atlas_id="health-connect-five-by-five",
            start_time=start,
            activity_type="running",
            distance_km=11.4,
            duration_minutes=64,
            average_speed_kmh=10.7,
            samples=samples,
        )

        groups = AtlasWorkoutExecutionMatcher._raw_speed_interval_groups(
            AtlasWorkoutExecutionMatcher._planned_intervals(planned),
            activity,
        )

        self.assertEqual(len(groups), 5)
        self.assertEqual(
            [round(item["duration_seconds"]) for item in groups],
            [300, 300, 300, 300, 300],
        )
        self.assertEqual(
            [round(item["raw_recovery_seconds"]) for item in groups[:-1]],
            [120, 120, 120, 120],
        )

    def test_detects_eight_three_minute_vo2_blocks(self) -> None:
        target = IntensityTarget(zone=5, speed_min_kmh=13.5, speed_max_kmh=14.8)
        planned = AdaptiveWorkout(
            workout_id="vo2-eight-by-three",
            workout_date=date(2026, 9, 12),
            workout_type=WorkoutType.VMA_LONG,
            title="VO₂max · 8 × 3 min",
            objective="Développer le temps de soutien VO₂max.",
            blocks=[TrainingBlock(
                "8 × 3 min", BlockType.WORK, 8, 3,
                recovery_minutes=1.5, target=target,
            )],
            planned_duration_minutes=58,
        )
        start = datetime(2026, 9, 12, 18, tzinfo=timezone.utc)
        samples = [
            ActivitySample(
                timestamp=start + timedelta(seconds=offset),
                speed_mps=9.8 / 3.6,
            )
            for offset in range(0, 12 * 60, 10)
        ]
        cursor = 12 * 60
        for repetition in range(8):
            for offset in range(0, 181, 10):
                samples.append(ActivitySample(
                    timestamp=start + timedelta(seconds=cursor + offset),
                    speed_mps=(13.7 + (repetition % 3) * .18) / 3.6,
                ))
            cursor += 180
            if repetition < 7:
                for offset in range(10, 91, 10):
                    samples.append(ActivitySample(
                        timestamp=start + timedelta(seconds=cursor + offset),
                        speed_mps=6.8 / 3.6,
                    ))
                cursor += 90
        activity = LongitudinalActivity(
            atlas_id="health-connect-eight-by-three",
            start_time=start,
            activity_type="running",
            distance_km=10.2,
            duration_minutes=56,
            average_speed_kmh=10.9,
            samples=samples,
        )

        groups = AtlasWorkoutExecutionMatcher._raw_speed_interval_groups(
            AtlasWorkoutExecutionMatcher._planned_intervals(planned),
            activity,
        )

        self.assertEqual(len(groups), 8)
        self.assertEqual(
            [round(item["raw_recovery_seconds"]) for item in groups[:-1]],
            [90, 90, 90, 90, 90, 90, 90],
        )

    def test_snaps_sparse_health_connect_recoveries_to_planned_boundary(self) -> None:
        planned = [{
            "duration_seconds": 180.0,
            "distance_meters": None,
            "recovery_minutes": 2.0,
            "planned": TrainingBlock(
                "3 min", BlockType.WORK, 1, 3,
                recovery_minutes=2,
                target=IntensityTarget(zone=5, speed_min_kmh=13.3),
            ),
        }] * 2
        groups = [
            {
                "start": 900.0, "end": 1080.0,
                "timeline_seconds": True, "block_type": "vma",
                "duration_seconds": 180.0, "distance_meters": 680.0,
                "average_speed_kmh": 13.6,
                "average_heart_rate_bpm": 148.0,
                "maximum_heart_rate_bpm": 155.0,
                "raw_recovery_seconds": 132.0,
            },
            {
                "start": 1212.0, "end": 1392.0,
                "timeline_seconds": True, "block_type": "vma",
                "duration_seconds": 180.0, "distance_meters": 690.0,
                "average_speed_kmh": 13.8,
                "average_heart_rate_bpm": 151.0,
                "maximum_heart_rate_bpm": 159.0,
            },
        ]

        details = AtlasWorkoutExecutionMatcher._align_interval_groups(
            planned, groups, blocks=[]
        )

        self.assertEqual(details[0]["recovery_seconds"], 120.0)

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

    def test_scores_aligned_recoveries_against_atlas_prescription(self) -> None:
        target = IntensityTarget(zone=4, speed_min_kmh=12, speed_max_kmh=13)
        planned = AdaptiveWorkout(
            workout_id="descending-threshold",
            workout_date=date(2026, 9, 3),
            workout_type=WorkoutType.THRESHOLD_SV2,
            title="SV2 descendant",
            objective="Respecter les paliers et leurs récupérations",
            blocks=[
                TrainingBlock("2000 m", BlockType.WORK, 1, 9.5, recovery_minutes=2, target=target),
                TrainingBlock("1600 m", BlockType.WORK, 1, 7.5, recovery_minutes=1.75, target=target),
                TrainingBlock("1200 m", BlockType.WORK, 1, 5.5, target=target),
            ],
            planned_duration_minutes=45,
        )
        activity = LongitudinalActivity(
            atlas_id="garmin-descending-threshold",
            start_time=datetime(2026, 9, 3, 17, tzinfo=timezone.utc),
            activity_type="running",
            distance_km=8,
            duration_minutes=45,
            workout_steps=[{"intensity": "active"}],
        )
        blocks = [
            SessionBlock(1, "sv2", 0, 570, 570, 2000, average_speed_kmh=12.63),
            SessionBlock(2, "recovery", 570, 690, 120, 159),
            SessionBlock(3, "sv2", 690, 1140, 450, 1600, average_speed_kmh=12.8),
            SessionBlock(4, "recovery", 1140, 1260, 120, 162),
            SessionBlock(5, "sv2", 1260, 1590, 330, 1200, average_speed_kmh=13.09),
            SessionBlock(6, "recovery", 1590, 2190, 600, 1505),
        ]
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=blocks,
            dominant_work_type="sv2",
            session_type="threshold",
            recovery_duration_seconds=840,
            workout_execution=WorkoutExecutionSummary(
                planned_repetition_count=3,
                completed_repetition_count=3,
                recovery_compliance_score=100,
            ),
        )

        result = AtlasWorkoutExecutionMatcher().match(planned, activity, analysis)

        self.assertEqual(result.execution.recovery_compliance_score, 93)
        self.assertIsNone(result.execution.interval_details[-1]["recovery_seconds"])
        self.assertEqual(result.score_audit["recovery"]["score"], 93)
        self.assertEqual(
            [item["planned_seconds"] for item in result.score_audit["recovery"]["recoveries"]],
            [120, 105],
        )
        self.assertEqual(
            [item["actual_seconds"] for item in result.score_audit["recovery"]["recoveries"]],
            [120, 120],
        )
        self.assertEqual(result.score_audit["execution"]["score"], result.execution.execution_score)

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

    def test_long_run_detects_late_specific_work_only(self) -> None:
        planned = AdaptiveWorkout(
            workout_id="long-run-late-specific-work",
            workout_date=date(2026, 9, 13),
            workout_type=WorkoutType.LONG_RUN,
            title="Sortie longue · 3 × 5 min en fin de séance",
            objective="Préserver la qualité sous fatigue.",
            blocks=[
                TrainingBlock(
                    "Endurance",
                    BlockType.CONTINUOUS,
                    1,
                    50,
                    target=IntensityTarget(zone=2),
                ),
                TrainingBlock(
                    "3 × 5 min sous SV2",
                    BlockType.WORK,
                    3,
                    5,
                    recovery_minutes=2,
                    target=IntensityTarget(
                        zone=3,
                        speed_min_kmh=11.8,
                        speed_max_kmh=12.6,
                    ),
                ),
            ],
            planned_duration_minutes=82,
        )
        activity = LongitudinalActivity(
            atlas_id="health-connect-long-run-late-work",
            start_time=datetime(2026, 9, 13, 8, tzinfo=timezone.utc),
            activity_type="running",
            distance_km=14.8,
            duration_minutes=82,
            average_speed_kmh=10.8,
        )
        analysis = DetailedSessionAnalysis(
            activity_id=activity.atlas_id,
            blocks=[
                SessionBlock(1, "z2", 0, 3000, 3000, 8500, average_speed_kmh=10.2),
                SessionBlock(2, "z3", 3000, 3300, 300, 1000, average_speed_kmh=12.0),
                SessionBlock(3, "recovery", 3300, 3420, 120, 230),
                SessionBlock(4, "z3", 3420, 3720, 300, 1010, average_speed_kmh=12.12),
                SessionBlock(5, "recovery", 3720, 3840, 120, 225),
                SessionBlock(6, "z3", 3840, 4140, 300, 1025, average_speed_kmh=12.3),
                SessionBlock(7, "z1", 4140, 4920, 780, 2810, average_speed_kmh=9.7),
            ],
            dominant_work_type="z3",
            session_type="long_run",
            recovery_duration_seconds=240,
        )

        result = AtlasWorkoutExecutionMatcher().match(planned, activity, analysis)

        self.assertEqual(result.execution.completed_repetition_count, 3)
        self.assertEqual(
            [item["start_seconds"] for item in result.execution.interval_details],
            [3000.0, 3420.0, 3840.0],
        )
        self.assertEqual(result.execution.recovery_compliance_score, 100)
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
            [
                (item["start_seconds"], item["end_seconds"])
                for item in result.execution.interval_details
            ],
            [
                (0.0, 280.0),
                (385.0, 665.0),
                (770.0, 1050.0),
                (1155.0, 1435.0),
            ],
        )
        self.assertEqual(
            [item["recovery_seconds"] for item in result.execution.interval_details[:-1]],
            [105.0, 105.0, 105.0],
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
