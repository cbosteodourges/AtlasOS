"""Tests de personnalisation depuis les compétitions passées."""

import unittest

from src.training.competition_history_personalizer import (
    CompetitionHistoryPersonalizer,
)


def analysis(
    distance: float,
    outcome: str,
    intensity_8w: int,
    intensity_4w: int,
) -> dict:
    return {
        "event": {
            "distance_km": distance,
            "outcome": outcome,
        },
        "eight_week_window": {
            "high_intensity_session_count": intensity_8w,
            "data_quality_score": 90,
        },
        "four_week_window": {
            "high_intensity_session_count": intensity_4w,
        },
        "taper": {
            "volume_change_percent": -49.3,
            "days_since_last_intensity_session": 5,
        },
    }


class CompetitionHistoryPersonalizerTests(unittest.TestCase):
    """Valide la priorité donnée aux préparations comparables."""

    def test_prioritizes_metabolic_quality_for_half_marathon(
        self,
    ) -> None:
        payload = {
            "analyses": [
                analysis(21.31, "successful", 5, 3),
                analysis(21.25, "failed", 1, 0),
                analysis(10.07, "successful_constrained", 5, 1),
            ]
        }

        result = CompetitionHistoryPersonalizer().build(
            payload,
            goal_distance_km=21.1,
        )

        self.assertTrue(result.prioritize_metabolic_quality)
        self.assertEqual(result.successful_analysis_count, 1)
        self.assertEqual(result.failed_analysis_count, 1)
        self.assertEqual(
            result.successful_intensity_sessions_8w,
            5.0,
        )
        self.assertEqual(
            result.failed_intensity_sessions_8w,
            1.0,
        )
        self.assertEqual(
            result.target_intensity_sessions_4w,
            3.0,
        )

    def test_stays_conservative_without_successful_reference(
        self,
    ) -> None:
        payload = {
            "analyses": [
                analysis(21.1, "failed", 1, 0),
            ]
        }

        result = CompetitionHistoryPersonalizer().build(
            payload,
            goal_distance_km=21.1,
        )

        self.assertFalse(result.prioritize_metabolic_quality)
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()