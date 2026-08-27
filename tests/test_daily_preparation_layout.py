import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DailyPreparationLayoutTests(unittest.TestCase):
    def test_form_fields_adapt_to_their_container_without_overflow(self):
        styles = (ROOT / "app" / "css" / "performance-running.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: repeat(2,minmax(0,1fr));", styles)
        self.assertIn(".daily-preparation-control-heading {\n  display: grid;", styles)
        self.assertEqual(styles.count("{"), styles.count("}"))

    def test_print_rules_do_not_recolour_the_live_training_interface(self):
        styles = (ROOT / "app" / "css" / "performance-running.css").read_text(encoding="utf-8")
        self.assertNotIn("body { background: white; color: black; }", styles)
        self.assertNotIn(".panel { border: 0; background: white; }", styles)

    def test_training_page_has_an_inline_dark_theme_guard(self):
        page = (ROOT / "app" / "performance-running.html").read_text(encoding="utf-8")
        self.assertIn('id="atlas-training-theme-guard"', page)
        self.assertIn("#planPanel.panel", page)
        self.assertIn("background: rgba(5,18,35,.96) !important", page)
        self.assertIn("repeat(2,minmax(0,1fr)) !important", page)


if __name__ == "__main__":
    unittest.main()
