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
            samples=samples,
            laps=laps,
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

if __name__ == "__main__":
    unittest.main()