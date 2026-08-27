import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AtlasCockpitNutritionUiTests(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / "app" / "atlas-cockpit.html").read_text(encoding="utf-8")
        self.script = (ROOT / "app" / "js" / "atlas-cockpit.js").read_text(encoding="utf-8")
        self.styles = (ROOT / "app" / "css" / "atlas-cockpit.css").read_text(encoding="utf-8")

    def test_founder_pilot_has_visible_daily_tools(self):
        for marker in ("NUTRITION &amp; HYDRATATION", 'data-water="250"', 'data-water="500"',
                       "data-nutrition-form", "data-hydration-progress"):
            self.assertIn(marker, self.page)
        self.assertIn("data-nutrition-nav", self.page)

    def test_module_uses_api_and_dashboard_preference(self):
        self.assertIn('/api/atlas/nutrition-hydration', self.script)
        self.assertIn("atlasNutritionPilotAdded", self.script)
        self.assertIn("nutritionNav.hidden = false", self.script)
        self.assertIn(".fuel-card", self.styles)


if __name__ == "__main__":
    unittest.main()
