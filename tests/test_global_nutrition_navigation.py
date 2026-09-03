import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GlobalNutritionNavigationTests(unittest.TestCase):
    def test_navigation_opens_the_single_dashboard_module_when_enabled(self):
        script = (ROOT / "app" / "js" / "atlas-global-nav.js").read_text(encoding="utf-8")
        module = (ROOT / "app" / "nutrition-hydration.html").read_text(encoding="utf-8")
        styles = (ROOT / "app" / "css" / "atlas-global-nav.css").read_text(encoding="utf-8")
        self.assertIn("./nutrition-hydration.html", script)
        self.assertIn("data-nutrition-root'", script)
        self.assertIn("/api/atlas/nutrition-hydration", script)
        self.assertIn("data-nutrition-form", module)
        self.assertIn("margin: auto 0 4px;", styles)


if __name__ == "__main__":
    unittest.main()
