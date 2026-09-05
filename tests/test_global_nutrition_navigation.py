import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GlobalNutritionNavigationTests(unittest.TestCase):
    def test_nutrition_module_is_archived_without_being_deleted(self):
        script = (ROOT / "app" / "js" / "atlas-global-nav.js").read_text(encoding="utf-8")
        module = (ROOT / "app" / "nutrition-hydration.html").read_text(encoding="utf-8")
        styles = (ROOT / "app" / "css" / "atlas-global-nav.css").read_text(encoding="utf-8")
        self.assertNotIn('label: "Nutrition"', script)
        self.assertNotIn("data-nutrition-root'", script)
        self.assertNotIn("/api/atlas/nutrition-hydration", script)
        self.assertIn("data-nutrition-form", module)
        self.assertIn("margin: auto 0 4px;", styles)


if __name__ == "__main__":
    unittest.main()
