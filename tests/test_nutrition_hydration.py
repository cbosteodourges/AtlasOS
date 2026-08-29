import unittest
from datetime import date

from src.physiology.nutrition_hydration import NutritionHydrationAnalyzer


class NutritionHydrationAnalyzerTests(unittest.TestCase):
    def test_empty_day_is_unknown_not_a_deficit(self):
        result = NutritionHydrationAnalyzer().analyze([], weight_kg=80, today=date(2026, 8, 27))
        self.assertEqual(result["today"]["record_count"], 0)
        self.assertIn("ne conclut pas à un déficit", result["recommendations"][0])
        self.assertEqual(result["confidence"], 0)

    def test_aggregates_health_connect_and_manual_records(self):
        records = [
            {"type": "hydration", "start_time": "2026-08-27T08:00:00+02:00",
             "volume_ml": 500, "source_device": "health.app"},
            {"type": "hydration", "start_time": "2026-08-27T10:00:00+02:00",
             "volume_ml": 250, "source": "atlas_manual"},
            {"type": "nutrition", "start_time": "2026-08-27T12:00:00+02:00",
             "energy_kcal": 650, "protein_g": 35, "carbohydrate_g": 80,
             "fat_g": 20, "source": "atlas_manual"},
        ]
        result = NutritionHydrationAnalyzer().analyze(
            records, weight_kg=80, exercise_minutes_today=60, today=date(2026, 8, 27)
        )
        self.assertEqual(result["today"]["hydration_ml"], 750)
        self.assertEqual(result["today"]["protein_g"], 35)
        self.assertEqual(result["targets"]["hydration_ml"], 3300)
        self.assertEqual(result["targets"]["protein_g"], 128)
        self.assertEqual(result["confidence"], 60)

    def test_expenditure_uses_profile_and_only_imported_sport_calories(self):
        result = NutritionHydrationAnalyzer().analyze(
            [], weight_kg=80, height_cm=180, age_years=40,
            biological_sex="male", activity_energy_kcal=720,
            activity_count=2, activity_calorie_count=1,
            measured_total_energy_kcal=2700,
            measured_active_energy_kcal=950,
            measured_basal_energy_kcal=1750,
            today=date(2026, 8, 27),
        )
        expenditure = result["energy_expenditure"]
        self.assertEqual(expenditure["basal_kcal"], 1750)
        self.assertEqual(expenditure["active_kcal"], 950)
        self.assertEqual(expenditure["sport_kcal"], 720)
        self.assertEqual(expenditure["known_total_kcal"], 2700)
        self.assertEqual(expenditure["total_source"], "health_connect")
        self.assertFalse(expenditure["sport_coverage_complete"])


if __name__ == "__main__":
    unittest.main()
