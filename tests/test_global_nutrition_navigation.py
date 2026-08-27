import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GlobalNutritionNavigationTests(unittest.TestCase):
    def test_navigation_opens_the_single_dashboard_module_when_enabled(self):
        script = (ROOT / "app" / "js" / "atlas-global-nav.js").read_text(encoding="utf-8")
        cockpit = (ROOT / "app" / "js" / "atlas-cockpit.js").read_text(encoding="utf-8")
        styles = (ROOT / "app" / "css" / "atlas-global-nav.css").read_text(encoding="utf-8")
        self.assertIn("./atlas-cockpit.html#nutrition-hydratation", script)
        self.assertIn("/api/atlas/nutrition-hydration", script)
        self.assertIn('location.hash === "#nutrition-hydratation"', cockpit)
        self.assertIn("margin: auto 0 14px;", styles)


if __name__ == "__main__":
    unittest.main()
