"""Tests du registre scientifique Atlas Research."""

import unittest

from src.research.training_protocol import (
    IntensityPattern,
    ProtocolApplicability,
    ProtocolBlockDefinition,
    TrainingProtocolRegistry,
    TrainingResearchProtocol,
)


def build_protocol(
    protocol_id: str = "vo2_triangular",
    *,
    phase: str = "specific",
    distance: float = 10.0,
    level: str = "competitive",
    confidence: int = 85,
) -> TrainingResearchProtocol:
    """Construit un protocole valide pour les tests."""
    return TrainingResearchProtocol(
        protocol_id=protocol_id,
        version="1.0",
        title="VO2 triangulaire",
        workout_type_key="triangular_vo2",
        summary="Bloc VO2 à intensité triangulaire.",
        objectives=["Développer la VO2max"],
        blocks=[
            ProtocolBlockDefinition(
                name="Bloc principal",
                repetitions=5,
                duration_seconds=180,
                recovery_seconds=120,
                intensity_basis="vma",
                intensity_min_percent=90,
                intensity_max_percent=105,
                intensity_pattern=IntensityPattern.TRIANGULAR,
            )
        ],
        applicability=ProtocolApplicability(
            suitable_phases=[phase],
            suitable_goal_distances_km=[distance],
            suitable_athlete_levels=[level],
        ),
        evidence_confidence_score=confidence,
    )


class TrainingProtocolRegistryTests(unittest.TestCase):
    """Validation du catalogue Atlas Research."""

    def test_registers_and_gets_protocol(self) -> None:
        registry = TrainingProtocolRegistry()
        protocol = build_protocol()

        registry.register(protocol)

        self.assertIs(registry.get("vo2_triangular"), protocol)

    def test_register_replaces_existing_protocol(self) -> None:
        registry = TrainingProtocolRegistry()
        registry.register(build_protocol(confidence=70))
        replacement = build_protocol(confidence=92)

        registry.register(replacement)

        self.assertIs(registry.get("vo2_triangular"), replacement)
        self.assertEqual(len(registry.list_all()), 1)

    def test_get_rejects_unknown_protocol(self) -> None:
        registry = TrainingProtocolRegistry()

        with self.assertRaisesRegex(
            KeyError,
            "Protocole Atlas Research inconnu",
        ):
            registry.get("unknown")

    def test_list_all_sorts_protocols_by_identifier(self) -> None:
        registry = TrainingProtocolRegistry()
        registry.register(build_protocol("protocol_z"))
        registry.register(build_protocol("protocol_a"))

        identifiers = [
            protocol.protocol_id
            for protocol in registry.list_all()
        ]

        self.assertEqual(
            identifiers,
            ["protocol_a", "protocol_z"],
        )

    def test_find_applicable_filters_context(self) -> None:
        registry = TrainingProtocolRegistry()
        expected = build_protocol()
        registry.register(expected)
        registry.register(
            build_protocol(
                "base_hills",
                phase="base",
                distance=21.1,
                level="recreational",
            )
        )

        result = registry.find_applicable(
            phase="specific",
            goal_distance_km=10.0,
            athlete_level="competitive",
        )

        self.assertEqual(result, [expected])

    def test_find_applicable_sorts_by_confidence(self) -> None:
        registry = TrainingProtocolRegistry()
        registry.register(
            build_protocol("lower_confidence", confidence=70)
        )
        registry.register(
            build_protocol("higher_confidence", confidence=95)
        )

        result = registry.find_applicable(
            phase="specific",
            goal_distance_km=10.0,
            athlete_level="competitive",
        )

        self.assertEqual(
            [protocol.protocol_id for protocol in result],
            ["higher_confidence", "lower_confidence"],
        )

    def test_register_rejects_invalid_protocol(self) -> None:
        registry = TrainingProtocolRegistry()
        protocol = build_protocol()
        protocol.evidence_confidence_score = 101

        with self.assertRaises(ValueError):
            registry.register(protocol)


if __name__ == "__main__":
    unittest.main()