import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"


class AtlasHealthUiTests(unittest.TestCase):
    def setUp(self):
        self.page = (APP_ROOT / "atlas-hub.html").read_text(encoding="utf-8")
        self.styles = (APP_ROOT / "css" / "atlas-health.css").read_text(encoding="utf-8")
        self.script = (APP_ROOT / "js" / "atlas-hub.js").read_text(encoding="utf-8")
        self.navigation = (APP_ROOT / "js" / "atlas-global-nav.js").read_text(encoding="utf-8")

    def test_health_has_three_clear_user_routes(self):
        for label in (
            "Signaler une douleur",
            "Prévention et charge",
            "L’histoire de votre corps",
        ):
            self.assertIn(label, self.page)
            self.assertIn(label, self.navigation)

    def test_health_views_do_not_inherit_the_hub_fixed_grid(self):
        self.assertIn("atlas-health.css?v=6", self.page)
        self.assertIn(".atlas-health-main{display:block;min-height:100vh}", self.styles)
        self.assertIn(".atlas-health-main>.view{padding:0;overflow:visible}", self.styles)
        self.assertIn(
            "body > main.app > section.main.atlas-health-main{",
            self.styles,
        )
        self.assertNotIn("body .app > main.main.atlas-health-main{", self.styles)

    def test_pain_reporting_covers_key_running_regions(self):
        for region in ("foot", "ankle", "leg", "knee", "thigh", "hip", "glute"):
            self.assertIn(f'data-region="{region}"', self.page)
        for structure in (
            "Tendon d’Achille",
            "Voûte plantaire",
            "Têtes des métatarsiens",
            "Tendon rotulien",
            "bandelette ilio-tibiale",
            "Interligne méniscal interne",
            "Piriforme",
        ):
            self.assertIn(structure, self.script)

    def test_advanced_anatomy_is_optional_and_lazy(self):
        self.assertIn("Voir l’anatomie avancée", self.page)
        self.assertIn('data-anatomy-panel hidden', self.page)
        self.assertIn("biomecanique.html?region=", self.script)
        self.assertIn("[data-anatomy-toggle]", self.styles)
        self.assertIn("display: none !important", self.styles)

    def test_prevention_uses_personal_history_not_a_diagnostic(self):
        self.assertIn("votre propre historique", self.page)
        self.assertIn("ne constitue ni un diagnostic ni une limite universelle", self.page)
        self.assertIn("ne le modifie pas en silence", self.page)
        self.assertIn("/api/atlas-coach/executions?limit=200", self.script)


if __name__ == "__main__":
    unittest.main()
