"""
Tests de l'analyse détaillée des séances FIT.
"""

import unittest
from datetime import datetime, timedelta

from src.connectors import ActivitySample
from src.performance import (
    AthleteProfile,
    DetailedSessionAnalyzer,
    LongitudinalActivity,
    SessionBlock,
)
from src.performance.athlete_profile import (
    PhysiologicalReferences,
)


class DetailedSessionAnalyzerTests(unittest.TestCase):
    """Vérifie la détection des blocs d'une séance."""

    def setUp(self) -> None:
        self.analyzer = DetailedSessionAnalyzer()
        self.start = datetime.fromisoformat(
            "2026-08-02T08:30:00+02:00"
        )
        self.profile = AthleteProfile(
            athlete_id="athlete-test",
            declared_level="intermediate",
            observed_level="intermediate",
            physiological=PhysiologicalReferences(
                maximum_heart_rate_bpm=180,
                threshold_heart_rate_bpm=160,
                vma_kmh=14,
                threshold_speed_kmh=12.8,
            ),
        )

    def _sample(
        self,
        seconds: int,
        speed_mps: float,
        distance_meters: float,
        heart_rate_bpm: float,
    ) -> ActivitySample:
        return ActivitySample(
            timestamp=(
                self.start
                + timedelta(seconds=seconds)
            ).isoformat(),
            speed_mps=speed_mps,
            distance_meters=distance_meters,
            heart_rate_bpm=heart_rate_bpm,
            cadence_spm=170,
            power_watts=350,
            ground_contact_time_ms=250,
            vertical_ratio_percent=8.5,
        )

    def test_detects_z2_acceleration_and_recovery(
        self,
    ) -> None:
        samples = [
            self._sample(0, 2.8, 0, 130),
            self._sample(10, 2.8, 28, 132),
            self._sample(20, 2.8, 56, 133),
            self._sample(30, 2.8, 84, 134),
            self._sample(40, 2.8, 112, 135),
            self._sample(50, 2.8, 140, 136),
            self._sample(60, 3.3, 173, 142),
            self._sample(70, 4.0, 213, 153),
            self._sample(80, 4.5, 258, 165),
            self._sample(90, 2.0, 278, 145),
            self._sample(100, 2.0, 298, 138),
            self._sample(110, 2.0, 318, 134),
            self._sample(120, 2.0, 338, 130),
            self._sample(130, 2.0, 358, 128),
            self._sample(140, 2.0, 378, 126),
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:detailed-test",
            start_time=self.start,
            activity_type="running",
            distance_km=0.378,
            duration_minutes=140 / 60,
            samples=samples,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        block_types = [
            block.block_type
            for block in result.blocks
        ]

        self.assertIn("z2", block_types)
        self.assertIn("acceleration", block_types)
        self.assertIn("recovery", block_types)
        self.assertGreater(
            result.physiological_load_score,
            0,
        )
        self.assertGreater(
            result.analysis_confidence_score,
            0,
        )
        self.assertTrue(any(
            "puissance" in text and "cadence" in text
            for text in result.interpretation
        ))

    def test_cycling_distance_laps_are_not_running_sprints(self) -> None:
        samples = [
            self._sample(0, 7.0, 0, 115),
            self._sample(3300, 7.3, 24250, 124),
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:cycling-road",
            start_time=self.start,
            activity_type="road",
            distance_km=24.25,
            duration_minutes=55,
            average_speed_kmh=26.45,
            average_heart_rate_bpm=124,
            maximum_heart_rate_bpm=156,
            samples=samples,
            laps=[
                {
                    "total_timer_time": 700,
                    "total_distance": 5000,
                    "enhanced_avg_speed": 7.14,
                    "lap_trigger": "distance",
                },
                {
                    "total_timer_time": 600,
                    "total_distance": 5000,
                    "enhanced_avg_speed": 8.33,
                    "lap_trigger": "distance",
                },
                {
                    "total_timer_time": 620,
                    "total_distance": 5000,
                    "enhanced_avg_speed": 8.06,
                    "lap_trigger": "distance",
                },
            ],
        )

        result = self.analyzer.analyze(activity, self.profile)

        self.assertEqual(result.session_type, "cycling")
        self.assertEqual(result.dominant_work_type, "cycling")
        self.assertEqual(len(result.blocks), 1)
        self.assertEqual(result.blocks[0].block_type, "cycling")
        self.assertAlmostEqual(result.work_distance_meters, 24250)
        self.assertFalse(result.threshold_observations)

    def test_cycling_isolated_heart_rate_spike_is_filtered(self) -> None:
        samples = [
            self._sample(second, 7.3, second * 7.3, heart_rate)
            for second, heart_rate in enumerate(
                [171, 168, 155, 138, 130] + [125] * 20 + [140] * 20
            )
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:cycling-spike",
            start_time=self.start,
            activity_type="road",
            distance_km=24.25,
            duration_minutes=55.2,
            average_speed_kmh=26.38,
            average_heart_rate_bpm=125,
            maximum_heart_rate_bpm=171,
            samples=samples,
        )

        profile = AthleteProfile(
            athlete_id="cycling-spike-profile",
            declared_level="intermediate",
            observed_level="intermediate",
            physiological=PhysiologicalReferences(
                maximum_heart_rate_bpm=145,
            ),
        )
        result = self.analyzer.analyze(activity, profile)

        self.assertEqual(activity.maximum_heart_rate_bpm, 171)
        self.assertEqual(result.blocks[0].maximum_heart_rate_bpm, 140)
        self.assertTrue(result.data_integrity.heart_rate_spike_filtered)
        self.assertEqual(result.data_integrity.raw_maximum_heart_rate_bpm, 171)
        self.assertEqual(result.data_integrity.corrected_maximum_heart_rate_bpm, 140)
        self.assertTrue(result.data_integrity.heart_rate_reliable)


    def test_observes_sv1_and_sv2_transitions(
        self,
    ) -> None:
        samples = []
        distance = 0.0

        for seconds in range(0, 630, 30):
            if seconds < 210:
                speed_mps = 2.83
                heart_rate = 136 + seconds / 105
            elif seconds < 420:
                speed_mps = 3.11
                heart_rate = 145 + (seconds - 210) / 105
            else:
                speed_mps = 3.56
                heart_rate = 158 + (seconds - 420) / 105

            samples.append(
                self._sample(
                    seconds,
                    speed_mps,
                    distance,
                    heart_rate,
                )
            )
            distance += speed_mps * 30

        activity = LongitudinalActivity(
            atlas_id="garmin:threshold-test",
            start_time=self.start,
            activity_type="running",
            distance_km=distance / 1000,
            duration_minutes=10,
            samples=samples,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        observations = {
            observation.threshold_name: observation
            for observation in result.threshold_observations
        }

        self.assertIn(
            "sv1",
            observations,
            [
                block.block_type
                for block in result.blocks
            ],
        )
        self.assertIn("sv2", observations)
        self.assertGreater(
            observations["sv1"].confidence_score,
            0,
        )
        self.assertGreater(
            observations["sv2"].confidence_score,
            0,
        )
        self.assertGreater(
            observations["sv1"].estimated_speed_kmh,
            10,
        )
        self.assertGreater(
            observations["sv2"].estimated_speed_kmh,
            observations["sv1"].estimated_speed_kmh,
        )

    def test_smooths_easy_pace_noise_without_false_recovery(
        self,
    ) -> None:
        samples = []
        distance = 0.0
        speeds = [
            2.50,
            2.53,
            2.56,
            2.51,
            2.55,
            2.52,
        ]

        for seconds in range(0, 181):
            speed_mps = speeds[
                seconds % len(speeds)
            ]
            samples.append(
                self._sample(
                    seconds,
                    speed_mps,
                    distance,
                    130 + seconds / 90,
                )
            )
            distance += speed_mps

        activity = LongitudinalActivity(
            atlas_id="garmin:easy-noise-test",
            start_time=self.start,
            activity_type="running",
            distance_km=distance / 1000,
            duration_minutes=3,
            samples=samples,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        block_types = [
            block.block_type
            for block in result.blocks
        ]

        self.assertNotIn(
            "acceleration",
            block_types,
        )
        self.assertNotIn(
            "recovery",
            block_types,
        )
        self.assertTrue(
            set(block_types).issubset({"z1", "z2"})
        )
        self.assertLessEqual(
            len(result.blocks),
            2,
        )

    def test_merges_short_zone_artifact(
        self,
    ) -> None:
        samples = []
        distance = 0.0

        for seconds in range(0, 181):
            speed_mps = (
                3.0
                if 100 <= seconds < 105
                else 2.8
            )
            samples.append(
                self._sample(
                    seconds,
                    speed_mps,
                    distance,
                    132,
                )
            )
            distance += speed_mps

        activity = LongitudinalActivity(
            atlas_id="garmin:micro-block-test",
            start_time=self.start,
            activity_type="running",
            distance_km=distance / 1000,
            duration_minutes=3,
            samples=samples,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        self.assertEqual(
            [
                block.block_type
                for block in result.blocks
            ],
            ["z2"],
        )

    def test_uses_manual_laps_as_primary_structure(
        self,
    ) -> None:
        laps = [
            {
                "message_index": 0,
                "lap_trigger": "distance",
                "start_time": self.start.isoformat(),
                "total_timer_time": 600,
                "total_distance": 1400,
                "enhanced_avg_speed": 2.33,
                "enhanced_max_speed": 3.0,
                "avg_heart_rate": 125,
                "max_heart_rate": 138,
            },
            {
                "message_index": 1,
                "lap_trigger": "manual",
                "start_time": (
                    self.start
                    + timedelta(seconds=600)
                ).isoformat(),
                "total_timer_time": 15,
                "total_distance": 65,
                "enhanced_avg_speed": 4.33,
                "enhanced_max_speed": 4.7,
                "avg_heart_rate": 150,
                "max_heart_rate": 162,
            },
            {
                "message_index": 2,
                "lap_trigger": "manual",
                "start_time": (
                    self.start
                    + timedelta(seconds=615)
                ).isoformat(),
                "total_timer_time": 90,
                "total_distance": 180,
                "enhanced_avg_speed": 2.0,
                "enhanced_max_speed": 2.4,
                "avg_heart_rate": 140,
                "max_heart_rate": 158,
            },
            {
                "message_index": 3,
                "lap_trigger": "manual",
                "start_time": (
                    self.start
                    + timedelta(seconds=705)
                ).isoformat(),
                "total_timer_time": 15,
                "total_distance": 68,
                "enhanced_avg_speed": 4.53,
                "enhanced_max_speed": 4.9,
                "avg_heart_rate": 152,
                "max_heart_rate": 164,
            },
            {
                "message_index": 4,
                "lap_trigger": "session_end",
                "start_time": (
                    self.start
                    + timedelta(seconds=720)
                ).isoformat(),
                "total_timer_time": 300,
                "total_distance": 800,
                "enhanced_avg_speed": 2.67,
                "enhanced_max_speed": 3.0,
                "avg_heart_rate": 132,
                "max_heart_rate": 145,
            },
        ]
        samples = [
            self._sample(0, 2.33, 0, 120),
            self._sample(1020, 2.67, 2513, 132),
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:manual-laps-test",
            start_time=self.start,
            activity_type="running",
            distance_km=2.513,
            duration_minutes=17,
            samples=samples * 1000,
            laps=laps,
            time_in_zones=[{}],
            data_quality_score=90,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        self.assertEqual(
            [
                block.block_type
                for block in result.blocks
            ],
            [
                "warm_up",
                "sprint",
                "recovery",
                "sprint",
                "cool_down",
            ],
        )
        self.assertEqual(
            len(result.blocks),
            len(laps),
        )
        self.assertGreaterEqual(
            result.analysis_confidence_score,
            80,
        )

    def test_repeated_sprints_are_dominant_stimulus(
        self,
    ) -> None:
        blocks = [
            SessionBlock(
                block_index=1,
                block_type="z1",
                start_offset_seconds=0,
                end_offset_seconds=600,
                duration_seconds=600,
                distance_meters=1400,
            )
        ]

        for index in range(2, 10):
            blocks.append(
                SessionBlock(
                    block_index=index,
                    block_type=(
                        "sprint"
                        if index % 2 == 0
                        else "acceleration"
                    ),
                    start_offset_seconds=600 + index * 15,
                    end_offset_seconds=615 + index * 15,
                    duration_seconds=15,
                    distance_meters=60,
                )
            )

        self.assertEqual(
            self.analyzer._dominant_type(blocks),
            "sprint_acceleration",
        )

    def test_classifies_main_running_session_families(self) -> None:
        def block(block_type: str, duration: float = 600) -> SessionBlock:
            return SessionBlock(
                block_index=1,
                block_type=block_type,
                start_offset_seconds=0,
                end_offset_seconds=duration,
                duration_seconds=duration,
                distance_meters=2000,
            )

        activity = LongitudinalActivity(
            atlas_id="garmin:families",
            start_time=self.start,
            activity_type="running",
            distance_km=8,
            duration_minutes=50,
        )
        cases = [
            ("z1", "recovery"),
            ("z2", "endurance"),
            ("z3", "tempo"),
            ("sv2", "threshold"),
            ("vma", "vma"),
        ]
        for block_type, expected in cases:
            with self.subTest(block_type=block_type):
                self.assertEqual(
                    self.analyzer._session_type(
                        activity, [block(block_type)], block_type
                    ),
                    expected,
                )

        long_activity = LongitudinalActivity(
            atlas_id="garmin:long-run",
            start_time=self.start,
            activity_type="running",
            distance_km=16,
            duration_minutes=95,
        )
        self.assertEqual(
            self.analyzer._session_type(
                long_activity, [block("z2", 5700)], "z2"
            ),
            "long_run",
        )

    def test_marks_easy_boundaries_around_intensity(self) -> None:
        blocks = [
            SessionBlock(1, "z1", 0, 900, 900, 2200),
            SessionBlock(2, "sv2", 900, 1380, 480, 1700),
            SessionBlock(3, "recovery", 1380, 1500, 120, 250),
            SessionBlock(4, "sv2", 1500, 1980, 480, 1700),
            SessionBlock(5, "z1", 1980, 2580, 600, 1400),
        ]

        result = self.analyzer._mark_session_boundaries(blocks)

        self.assertEqual(result[0].block_type, "warm_up")
        self.assertEqual(result[-1].block_type, "cool_down")

    def test_uses_automatic_laps_before_raw_points(
        self,
    ) -> None:
        laps = [
            {
                "message_index": 0,
                "lap_trigger": "distance",
                "total_timer_time": 360,
                "total_distance": 1000,
                "enhanced_avg_speed": 2.78,
                "avg_heart_rate": 130,
            },
            {
                "message_index": 1,
                "lap_trigger": "distance",
                "total_timer_time": 350,
                "total_distance": 1000,
                "enhanced_avg_speed": 2.86,
                "avg_heart_rate": 135,
            },
            {
                "message_index": 2,
                "lap_trigger": "session_end",
                "total_timer_time": 180,
                "total_distance": 500,
                "enhanced_avg_speed": 2.78,
                "avg_heart_rate": 132,
            },
        ]
        samples = [
            self._sample(0, 2.78, 0, 125),
            self._sample(890, 2.78, 2500, 132),
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:auto-laps-test",
            start_time=self.start,
            activity_type="running",
            distance_km=2.5,
            duration_minutes=890 / 60,
            samples=samples * 1000,
            laps=laps,
            time_in_zones=[{}],
            data_quality_score=90,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        self.assertEqual(
            len(result.blocks),
            3,
        )
        self.assertEqual(
            result.blocks[0].block_type,
            "warm_up",
        )
        self.assertEqual(
            result.blocks[-1].block_type,
            "cool_down",
        )
        self.assertLessEqual(
            result.analysis_confidence_score,
            85,
        )

    def test_compares_structured_workout_with_execution(
        self,
    ) -> None:
        workout = [{
            "wkt_name": "2 x 40 s rapide",
            "num_valid_steps": 5,
            "capabilities": "tcx",
            "9": 1,
        }]
        workout_steps = [
            {
                "message_index": 0,
                "duration_type": "time",
                "duration_time": 600,
                "intensity": "warmup",
            },
            {
                "message_index": 1,
                "duration_type": "time",
                "duration_time": 40,
                "target_type": "speed",
                "custom_target_speed_low": 4.2,
                "custom_target_speed_high": 4.6,
                "intensity": "active",
            },
            {
                "message_index": 2,
                "duration_type": "time",
                "duration_time": 120,
                "intensity": "recovery",
            },
            {
                "message_index": 3,
                "duration_type": "repeat_until_steps_cmplt",
                "duration_step": 1,
                "repeat_steps": 2,
            },
            {
                "message_index": 4,
                "duration_type": "time",
                "duration_time": 300,
                "intensity": "cooldown",
            },
        ]
        laps = [
            {
                "message_index": 0,
                "lap_trigger": "distance",
                "total_timer_time": 381,
                "total_distance": 1000,
                "enhanced_avg_speed": 2.62,
            },
            {
                "message_index": 1,
                "lap_trigger": "workout_step",
                "total_timer_time": 222,
                "total_distance": 600,
                "enhanced_avg_speed": 2.70,
            },
            {
                "message_index": 1,
                "lap_trigger": "workout_step",
                "total_timer_time": 38,
                "total_distance": 170,
                "enhanced_avg_speed": 4.47,
            },
            {
                "message_index": 2,
                "lap_trigger": "workout_step",
                "total_timer_time": 122,
                "total_distance": 280,
                "enhanced_avg_speed": 2.30,
            },
            {
                "message_index": 3,
                "lap_trigger": "workout_step",
                "total_timer_time": 42,
                "total_distance": 185,
                "enhanced_avg_speed": 4.40,
            },
            {
                "message_index": 4,
                "lap_trigger": "workout_step",
                "total_timer_time": 118,
                "total_distance": 270,
                "enhanced_avg_speed": 2.29,
            },
            {
                "message_index": 5,
                "lap_trigger": "session_end",
                "total_timer_time": 302,
                "total_distance": 800,
                "enhanced_avg_speed": 2.65,
            },
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:structured-workout-test",
            start_time=self.start,
            activity_type="running",
            distance_km=3.305,
            duration_minutes=1225 / 60,
            samples=[
                self._sample(0, 2.65, 0, 120),
                self._sample(1225, 2.65, 3305, 145),
            ],
            laps=laps,
            workout=workout,
            workout_steps=workout_steps,
            data_quality_score=95,
        )

        result = self.analyzer.analyze(
            activity,
            self.profile,
        )

        self.assertEqual(
            result.workout_execution.workout_name,
            "2 x 40 s rapide",
        )
        self.assertEqual(
            result.workout_execution.workout_origin,
            "user_created",
        )
        self.assertGreaterEqual(
            result.workout_execution.origin_confidence_score,
            90,
        )
        self.assertEqual(
            result.workout_execution.planned_repetition_count,
            2,
        )
        self.assertEqual(
            result.workout_execution.completed_repetition_count,
            2,
        )
        self.assertEqual(
            result.workout_execution.countdown_tolerance_seconds,
            5,
        )
        self.assertGreaterEqual(
            result.workout_execution.execution_score,
            80,
        )
        self.assertEqual(len(result.blocks), 6)
        self.assertAlmostEqual(
            result.blocks[0].duration_seconds,
            603,
        )
        self.assertAlmostEqual(
            result.blocks[0].distance_meters,
            1600,
        )
        self.assertFalse(any(
            block.duration_seconds == 381
            for block in result.blocks
        ))
        self.assertTrue(
            any(
                "progression prudente" in influence
                for influence in result.planning_influences
            )
        )

    def test_detects_work_duration_inside_composite_manual_lap(
        self,
    ) -> None:
        samples = [
            self._sample(
                second,
                3.4 if second < 302 else 2.0,
                second * 3.4,
                140,
            )
            for second in range(422)
        ]
        activity = LongitudinalActivity(
            atlas_id="garmin:composite-manual-lap",
            start_time=self.start,
            activity_type="running",
            distance_km=1.3,
            duration_minutes=422 / 60,
            samples=samples,
            workout_steps=[{
                "message_index": 0,
                "duration_type": "time",
                "duration_time": 360,
                "custom_target_speed_low": 3.3,
                "custom_target_speed_high": 3.5,
                "intensity": "active",
            }],
        )
        block = SessionBlock(
            block_index=1,
            block_type="z3",
            start_offset_seconds=0,
            end_offset_seconds=420.694,
            duration_seconds=420.694,
            distance_meters=1241.87,
            detection_reasons=[
                "Tour manuel marqué par l'athlète."
            ],
        )

        duration = self.analyzer._structured_partial_work_duration(
            activity,
            samples,
            [block],
            12.8,
        )

        self.assertEqual(duration, 302.0)

    def test_flags_heart_rate_above_declared_limit(
        self,
    ) -> None:
        activity = LongitudinalActivity(
            atlas_id="garmin:heart-rate-anomaly",
            start_time=self.start,
            activity_type="running",
            distance_km=5,
            duration_minutes=30,
            average_heart_rate_bpm=176,
            maximum_heart_rate_bpm=188,
            average_speed_kmh=10,
            samples=[
                self._sample(0, 2.78, 0, 174),
                self._sample(1800, 2.78, 5000, 188),
            ],
            data_quality_score=90,
        )

        profile = AthleteProfile(
            athlete_id="athlete-heart-rate-test",
            declared_level="intermediate",
            observed_level="intermediate",
            physiological=PhysiologicalReferences(
                maximum_heart_rate_bpm=170,
                vma_kmh=14,
                threshold_speed_kmh=12.8,
            ),
        )
        result = self.analyzer.analyze(
            activity,
            profile,
        )

        self.assertFalse(
            result.data_integrity.heart_rate_reliable
        )
        self.assertFalse(
            result.data_integrity.physiological_data_usable
        )
        self.assertTrue(
            any(
                "170" in anomaly
                for anomaly
                in result.data_integrity.anomalies
            )
        )
        self.assertEqual(
            result.data_integrity.recommended_action,
            "exclude_heart_rate",
        )

if __name__ == "__main__":
    unittest.main()
