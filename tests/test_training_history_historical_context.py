"""Tests de la référence de charge issue des préparations antérieures."""

import unittest
from datetime import date, timedelta

from src.training.training_history_fusion import (
    FusedActivityResponse,
    TrainingHistoryFusionAnalyzer,
)


def activity(day: date, load: float) -> FusedActivityResponse:
    return FusedActivityResponse(
        activity_id=day.isoformat(),
        activity_date=day,
        original_sport="running",
        canonical_sport="running",
        session_type="threshold",
        duration_minutes=50,
        distance_km=9,
        elevation_gain_m=0,
        physiological_load_score=load,
        biomechanical_load_score=load,
        intensity_score=load,
        session_load_units=load,
    )


class HistoricalLoadContextTests(unittest.TestCase):

    def test_identifies_return_after_artificially_light_period(self) -> None:
        analysis_day = date(2026, 8, 27)
        weekly_loads = [170, 185, 160, 190, 175, 180]
        records = []
        for week_index, load in enumerate(weekly_loads, start=5):
            records.append(activity(
                analysis_day - timedelta(days=week_index * 7),
                load,
            ))

        context = TrainingHistoryFusionAnalyzer._historical_load_context(
            records,
            analysis_date=analysis_day,
            acute_load=177.5,
            recent_reference=112.4,
        )

        self.assertEqual(context["status"], "return_to_preparation_load")
        self.assertGreater(context["comparable_week_count"], 0)
        self.assertTrue(context["recent_reference_depressed"])

    def test_flags_load_above_every_previous_preparation(self) -> None:
        analysis_day = date(2026, 8, 27)
        records = [
            activity(analysis_day - timedelta(days=offset), load)
            for offset, load in zip((35, 42, 49, 56), (90, 100, 110, 120))
        ]

        context = TrainingHistoryFusionAnalyzer._historical_load_context(
            records,
            analysis_date=analysis_day,
            acute_load=150,
            recent_reference=105,
        )

        self.assertEqual(context["status"], "above_personal_history")


if __name__ == "__main__":
    unittest.main()
