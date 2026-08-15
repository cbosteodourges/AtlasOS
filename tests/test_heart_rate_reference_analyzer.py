"""Tests du moteur cardiaque longitudinal Atlas."""
from datetime import datetime
import unittest
from src.performance.heart_rate_reference_analyzer import HeartRateReferenceAnalyzer
from src.performance.longitudinal_models import LongitudinalActivity

class HeartRateReferenceAnalyzerTests(unittest.TestCase):
    def activity(self, identifier, year, maximum, quality=90, activity_type="running"):
        return LongitudinalActivity(
            atlas_id=identifier,
            start_time=datetime(year, 6, 15, 10, 0),
            activity_type=activity_type,
            distance_km=10.0,
            duration_minutes=55.0,
            average_heart_rate_bpm=140.0,
            maximum_heart_rate_bpm=maximum,
            data_quality_score=quality,
        )

    def test_latest_coherent_annual_peak(self):
        values = [(2023,173),(2023,169),(2024,172),(2024,168),
                  (2025,171),(2025,167),(2026,170),(2026,168)]
        activities = [self.activity(f"a-{index}", year, peak)
                      for index, (year, peak) in enumerate(values)]
        result = HeartRateReferenceAnalyzer().analyze(activities, age_years=50)
        self.assertEqual(result.maximum_heart_rate_bpm, 170)
        self.assertEqual([item.heart_rate_bpm for item in result.annual_peaks],
                         [173, 172, 171, 170])
        self.assertEqual(result.source, "longitudinal")
        self.assertGreaterEqual(result.confidence_score, 75)

    def test_rejects_isolated_foreign_peak(self):
        activities = [
            self.activity("personal-1", 2025, 171),
            self.activity("personal-2", 2025, 168),
            self.activity("personal-3", 2026, 170),
            self.activity("personal-4", 2026, 167),
            self.activity("daughter-watch", 2026, 198),
        ]
        result = HeartRateReferenceAnalyzer().analyze(activities, age_years=50)
        self.assertEqual(result.maximum_heart_rate_bpm, 170)
        self.assertEqual(result.rejected_activity_ids, ["daughter-watch"])
        self.assertNotEqual(result.observed_peak_bpm, 198)

    def test_theory_is_only_a_low_confidence_fallback(self):
        result = HeartRateReferenceAnalyzer().analyze([], age_years=50)
        self.assertEqual(result.theoretical_220_minus_age_bpm, 170.0)
        self.assertEqual(result.theoretical_210_minus_065_age_bpm, 177.5)
        self.assertEqual(result.maximum_heart_rate_bpm, 174)
        self.assertEqual(result.source, "theoretical_prior")
        self.assertEqual(result.confidence_score, 25)

    def test_ignores_wrong_sport_and_low_quality(self):
        activities = [
            self.activity("cycling", 2026, 190, activity_type="cycling"),
            self.activity("poor", 2026, 205, quality=20),
            self.activity("valid", 2026, 169),
        ]
        result = HeartRateReferenceAnalyzer().analyze(activities, age_years=50)
        self.assertEqual(result.maximum_heart_rate_bpm, 169)
        self.assertEqual(result.accepted_observation_count, 1)

if __name__ == "__main__":
    unittest.main()
