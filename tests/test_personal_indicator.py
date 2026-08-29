import unittest

from src.physiology.personal_indicator import PersonalIndicatorInterpreter


class PersonalIndicatorInterpreterTests(unittest.TestCase):
    def test_answers_the_five_atlas_questions(self):
        result = PersonalIndicatorInterpreter.interpret(
            indicator="sleep",
            current={"hours": 7.5},
            personal_reference="8 h",
            optimal_zone="7 h 50 à 8 h 20",
            evolution="30 min sous la référence",
            probable_consequence="Fatigue diurne possible",
            recommendation="Viser 30 min de sommeil supplémentaire",
            favorability_score=88,
            confidence=90,
            data_complete=False,
            missing_data=["VFC nocturne"],
        )

        self.assertEqual(result["status"], "monitor")
        self.assertEqual(result["status_label"], "À surveiller")
        self.assertEqual(
            result["display_label"],
            "Bonne récupération probable · à confirmer",
        )
        self.assertEqual(
            set(result["five_questions"]),
            {"reference", "optimal", "evolution", "consequence", "advice"},
        )

    def test_marks_complete_favorable_measure_as_optimal(self):
        result = PersonalIndicatorInterpreter.interpret(
            indicator="recovery",
            current={"atlas_index": 90},
            personal_reference="Référence personnelle",
            optimal_zone="Zone apprise",
            evolution="Stable",
            probable_consequence="Favorable",
            recommendation="Maintenir",
            favorability_score=90,
            confidence=88,
            data_complete=True,
        )
        self.assertEqual(result["status"], "optimal")
        self.assertEqual(result["display_label"], "Conditions optimales")


if __name__ == "__main__":
    unittest.main()
