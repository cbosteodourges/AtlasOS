"""Tests de l’interprétation du ressenti post-séance."""

import unittest

from src.training.post_workout_context_analyzer import (
    PostWorkoutContextAnalyzer,
)


class PostWorkoutContextAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = PostWorkoutContextAnalyzer()

    def test_external_constraints_do_not_penalize_fitness_alone(self):
        result = self.analyzer.analyze({
            "overall_sensation_0_to_10": 7,
            "perceived_effort_0_to_10": 6,
            "heat_0_to_10": 8,
            "relief_0_to_10": 7,
            "pain_0_to_10": 1,
            "fatigue_0_to_10": 3,
        })
        self.assertEqual(result.action, "maintain")
        self.assertEqual(len(result.external_constraints), 2)

    def test_high_pain_prioritizes_recovery(self):
        result = self.analyzer.analyze({
            "overall_sensation_0_to_10": 5,
            "perceived_effort_0_to_10": 7,
            "pain_0_to_10": 8,
            "fatigue_0_to_10": 4,
        })
        self.assertEqual(result.status, "alert")
        self.assertEqual(result.action, "recovery_priority")
        self.assertLess(result.next_load_factor, .7)

    def test_difficult_response_proposes_reduction(self):
        result = self.analyzer.analyze({
            "overall_sensation_0_to_10": 3,
            "perceived_effort_0_to_10": 9,
            "pain_0_to_10": 2,
            "fatigue_0_to_10": 6,
        })
        self.assertEqual(result.action, "reduce_next_intensity")
        self.assertTrue(result.requires_user_validation)


if __name__ == "__main__":
    unittest.main()
