import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UnifiedWorkoutDecisionUiTests(unittest.TestCase):
    def test_training_uses_the_session_decision_instead_of_sidebar_duplicate(self):
        navigation = (ROOT / "app" / "js" / "atlas-global-nav.js").read_text(encoding="utf-8")
        calendar = (ROOT / "app" / "js" / "atlas-training-calendar.js").read_text(encoding="utf-8")
        self.assertIn('${isCoach ? "" : `<button class="atlas-talk-button"', navigation)
        self.assertIn("Quelle séance choisissez-vous ?", calendar)
        self.assertIn('data-daily-selection="keep_original"', calendar)
        self.assertIn('data-daily-selection="accept_adaptation"', calendar)
        self.assertIn("Qu’avez-vous réellement effectué ?", calendar)

    def test_cockpit_uses_the_same_adaptation_button_markup(self):
        cockpit = (ROOT / "app" / "atlas-cockpit.html").read_text(encoding="utf-8")
        self.assertIn('class="atlas-talk-button"', cockpit)
        self.assertIn('class="atlas-talk-orb"', cockpit)
        self.assertIn("Ressenti et choix guidé", cockpit)


if __name__ == "__main__":
    unittest.main()
