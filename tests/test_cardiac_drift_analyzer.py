"""Tests de l'analyse individualisée de dérive cardiaque."""

import unittest
from datetime import datetime, timedelta, timezone

from src.connectors.activity_schema import ActivitySample
from src.performance.cardiac_drift_analyzer import (
    CardiacDriftAnalyzer,
)
from src.performance.longitudinal_models import (
    LongitudinalActivity,
)


class CardiacDriftAnalyzerTests(unittest.TestCase):
    """Vérifie le découplage vitesse–fréquence cardiaque."""

    @staticmethod
    def _activity(
        duration_minutes: int = 50,
    ) -> LongitudinalActivity:
        start = datetime(
            2026,
            8,
            11,
            18,
            0,
            tzinfo=timezone.utc,
        )
        samples = []

        for second in range(duration_minutes * 60):
            elapsed_minutes = second / 60
            heart_rate = (
                120
                if elapsed_minutes < 12
                else (
                    128
                    if elapsed_minutes < 31
                    else 134
                )
            )
            samples.append(
                ActivitySample(
                    timestamp=(
                        start + timedelta(seconds=second)
                    ).isoformat(),
                    heart_rate_bpm=heart_rate,
                    speed_mps=2.85,
                    altitude_m=40.0,
                    distance_meters=second * 2.85,
                    temperature_c=26.0,
                )
            )

        return LongitudinalActivity(
            atlas_id="garmin:test-drift",
            start_time=start,
            activity_type="running",
            distance_km=8.5,
            duration_minutes=float(duration_minutes),
            samples=samples,
        )

    def test_detects_notable_drift_after_warmup(self) -> None:
        result = CardiacDriftAnalyzer().analyze(
            self._activity()
        )

        self.assertTrue(result.analyzable)
        self.assertEqual(
            result.warmup_excluded_minutes,
            12.0,
        )
        self.assertGreater(
            result.heart_rate_change_bpm,
            5.0,
        )
        self.assertGreater(
            result.aerobic_decoupling_percent,
            4.0,
        )
        self.assertEqual(
            result.drift_classification,
            "controlled",
        )
        self.assertGreaterEqual(
            result.confidence_score,
            80,
        )

    def test_rejects_short_activity(self) -> None:
        result = CardiacDriftAnalyzer().analyze(
            self._activity(duration_minutes=20)
        )

        self.assertFalse(result.analyzable)
        self.assertTrue(result.limitations)

    def test_rejects_non_running_activity(self) -> None:
        activity = self._activity()
        activity.activity_type = "cycling"

        result = CardiacDriftAnalyzer().analyze(activity)

        self.assertFalse(result.analyzable)
        self.assertIn(
            "Analyse réservée aux activités de course.",
            result.limitations,
        )


if __name__ == "__main__":
    unittest.main()