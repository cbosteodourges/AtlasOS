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
        self.assertIn("atlas-health.css?v=9", self.page)
        self.assertIn(".atlas-health-main{display:block;min-height:100vh}", self.styles)
        self.assertIn(".atlas-health-main>.view{padding:0;overflow:visible}", self.styles)
        self.assertIn(
            "body > main.app > section.main.atlas-health-main{",
            self.styles,
        )
        self.assertNotIn("body .app > main.main.atlas-health-main{", self.styles)

    def test_pain_reporting_covers_key_running_regions(self):
        for region in ("foot", "ankle", "leg", "knee", "thigh", "hip", "glute"):
            self.assertIn(f'{region}:', self.script)
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

    def test_regional_anatomy_is_professional_interactive_and_synchronised(self):
        self.assertIn('data-regional-anatomy', self.page)
        self.assertIn('data-anatomy-board', self.page)
        self.assertIn('clinical-region-map', self.page)
        self.assertNotIn('avatar-regions', self.page)
        self.assertIn('medical-plate', self.script)
        self.assertIn('anatomy-overlay', self.script)
        self.assertIn('const anatomyPlans = {', self.script)
        for region in ("foot", "ankle"):
            self.assertIn(f"    {region}: {{", self.script)
        for view in ("Face et dessus du pied", "Profil · os et ligaments", "Repérage de surface"):
            self.assertIn(view, self.script)
        self.assertIn("selectAnatomyZone", self.script)
        self.assertIn("syncAnatomySelection", self.script)
        self.assertIn(".medical-plate-visual", self.styles)
        self.assertIn("Servier Medical Art", self.script)
        self.assertNotIn("repère numéroté", self.script)

    def test_servier_assets_and_attribution_are_bundled(self):
        asset_root = APP_ROOT / "assets" / "anatomy" / "servier"
        for filename in ("foot-ankle-anterior.png", "foot-ankle-lateral-deep.png"):
            self.assertTrue((asset_root / filename).is_file())
        attribution = (asset_root / "ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn("CC BY 4.0", attribution)
        self.assertIn("https://smart.servier.com/", attribution)

    def test_prevention_uses_personal_history_not_a_diagnostic(self):
        self.assertIn("votre propre historique", self.page)
        self.assertIn("ne constitue ni un diagnostic ni une limite universelle", self.page)
        self.assertIn("ne le modifie pas en silence", self.page)
        self.assertIn("/api/atlas-coach/executions?limit=200", self.script)


if __name__ == "__main__":
    unittest.main()
