import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AtlasCockpitNutritionUiTests(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / "app" / "atlas-cockpit.html").read_text(encoding="utf-8")
        self.module = (ROOT / "app" / "nutrition-hydration.html").read_text(encoding="utf-8")
        self.script = (ROOT / "app" / "js" / "nutrition-hydration.js").read_text(encoding="utf-8")
        self.styles = (ROOT / "app" / "css" / "nutrition-hydration.css").read_text(encoding="utf-8")
        self.cockpit_script = (ROOT / "app" / "js" / "atlas-cockpit.js").read_text(encoding="utf-8")
        self.cockpit_styles = (ROOT / "app" / "css" / "atlas-cockpit.css").read_text(encoding="utf-8")

    def test_founder_pilot_has_visible_daily_tools(self):
        for marker in ("Nutrition &amp; Hydratation", 'data-water="250"', 'data-water="500"',
                       "data-nutrition-form", "data-hydration-progress"):
            self.assertIn(marker, self.module)
        self.assertIn("data-nutrition-nav", self.page)

    def test_module_uses_api_and_dashboard_preference(self):
        self.assertIn('/api/atlas/nutrition-hydration', self.script)
        self.assertIn("data-nutrition-form", self.script)
        self.assertIn(".daily-summary", self.styles)

    def test_cockpit_appearance_presets_are_local_and_non_destructive(self):
        for theme in ("night", "ocean", "graphite", "aurora", "forest", "violet", "ember", "deepsea", "lagoon", "plum", "rose", "sand-card", "frost", "white"):
            self.assertIn(f'value="{theme}"', self.page)
        self.assertIn("atlasAppearanceTheme", self.cockpit_script)
        self.assertIn("localStorage.setItem(themeKey", self.cockpit_script)
        self.assertIn('body[data-atlas-theme="ocean"]', self.cockpit_styles)
        for canvas in ("cosmos", "pearl", "mist", "sand", "ice", "sage", "white", "sky", "lavender", "blush", "slate"):
            self.assertIn(f'value="{canvas}"', self.page)
            self.assertIn(f'body[data-atlas-canvas="{canvas}"]', self.cockpit_styles)
        self.assertIn("atlasAppearanceCanvas", self.cockpit_script)
        self.assertIn("localStorage.setItem(canvasKey", self.cockpit_script)
        for sidebar in ("atlas", "ocean", "graphite", "forest", "violet", "copper", "ice", "pearl"):
            self.assertIn(f'value="{sidebar}"', self.page)
            self.assertIn(f'body[data-atlas-sidebar="{sidebar}"]', self.cockpit_styles)
        self.assertIn("atlasAppearanceSidebar", self.cockpit_script)
        self.assertIn("localStorage.setItem(sidebarKey", self.cockpit_script)

    def test_cockpit_displays_endurance_family_progression(self):
        self.assertIn("data-family-progression", self.page)
        self.assertIn("data-family-chart", self.page)
        self.assertIn("family_progression", self.cockpit_script)
        self.assertIn("equivalent_speed_kmh", self.cockpit_script)


if __name__ == "__main__":
    unittest.main()
