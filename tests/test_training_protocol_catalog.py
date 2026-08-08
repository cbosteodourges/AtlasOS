"""Tests du catalogue initial Atlas Research."""

import unittest

from src.research.training_protocol import IntensityPattern
from src.research.training_protocol_catalog import (
    build_default_training_protocol_registry,
    build_hill_sprints_protocol,
    build_mixed_threshold_vo2_protocol,
    build_triangular_vo2_protocol,
)


class TrainingProtocolCatalogTests(unittest.TestCase):
    """Validation des protocoles scientifiques initiaux."""

    def test_default_registry_contains_three_protocols(
        self,
    ) -> None:
        registry = build_default_training_protocol_registry()

        identifiers = [
            protocol.protocol_id
            for protocol in registry.list_all()
        ]

        self.assertEqual(
            identifiers,
            [
                "hill_sprints_v1",
                "mixed_threshold_vo2_v1",
                "triangular_vo2_v1",
            ],
        )

    def test_protocols_match_supported_workout_types(
        self,
    ) -> None:
        registry = build_default_training_protocol_registry()

        workout_type_keys = {
            protocol.workout_type_key
            for protocol in registry.list_all()
        }

        self.assertEqual(
            workout_type_keys,
            {
                "hill_sprints",
                "mixed_threshold_vo2",
                "triangular_vo2",
            },
        )

    def test_all_default_protocols_are_valid(self) -> None:
        registry = build_default_training_protocol_registry()

        for protocol in registry.list_all():
            protocol.validate()

    def test_hill_sprints_define_gradient_and_risks(
        self,
    ) -> None:
        protocol = build_hill_sprints_protocol()
        block = protocol.blocks[0]

        self.assertEqual(block.gradient_min_percent, 6)
        self.assertEqual(block.gradient_max_percent, 10)
        self.assertEqual(
            block.intensity_pattern,
            IntensityPattern.HILL_ACCELERATION,
        )
        self.assertIn(
            "douleur_achille_active",
            protocol.applicability.contraindications,
        )

    def test_mixed_protocol_contains_threshold_and_vo2_blocks(
        self,
    ) -> None:
        protocol = build_mixed_threshold_vo2_protocol()

        self.assertEqual(len(protocol.blocks), 2)
        self.assertEqual(
            [block.intensity_basis for block in protocol.blocks],
            ["individual_threshold_speed", "vma"],
        )

    def test_triangular_protocol_is_marked_as_experimental(
        self,
    ) -> None:
        protocol = build_triangular_vo2_protocol()

        self.assertEqual(
            protocol.blocks[0].intensity_pattern,
            IntensityPattern.TRIANGULAR,
        )
        self.assertLess(protocol.evidence_confidence_score, 60)
        self.assertTrue(protocol.research_notes)

    def test_applicable_protocols_are_ranked_by_evidence(
        self,
    ) -> None:
        registry = build_default_training_protocol_registry()

        result = registry.find_applicable(
            phase="development",
            goal_distance_km=10.0,
            athlete_level="competitive",
        )

        self.assertEqual(
            [protocol.protocol_id for protocol in result],
            [
                "mixed_threshold_vo2_v1",
                "hill_sprints_v1",
                "triangular_vo2_v1",
            ],
        )


if __name__ == "__main__":
    unittest.main()