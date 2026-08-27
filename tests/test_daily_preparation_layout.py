import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DailyPreparationLayoutTests(unittest.TestCase):
    def test_form_fields_adapt_to_their_container_without_overflow(self):
        styles = (ROOT / "app" / "css" / "performance-running.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: repeat(2,minmax(0,1fr));", styles)
        self.assertIn(".daily-preparation-control-heading {\n  display: grid;", styles)
        self.assertEqual(styles.count("{"), styles.count("}"))


if __name__ == "__main__":
    unittest.main()
