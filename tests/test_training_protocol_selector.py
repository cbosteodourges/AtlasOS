"""Tests de sélection individualisée Atlas Research."""

import unittest

from src.performance.athlete_profile import (
    AthleteProfile,
    PhysiologicalReferences,
    TrainingTolerance,
)
from src.research.training_protocol_catalog import (
    build_default_training_protocol_registry,
)
from src.research.training_protocol_selector import (
    TrainingProtocolSelector,
)


def build_profile(
    *,
    pain: bool = False,
    with_metrics: bool = True,
) -> AthleteProfile:
    """Construit un profil compétitif pour les tests."""
    physiological = PhysiologicalReferences()

    if with_metrics:
        physiological.vma_kmh = 14.0
        physiological.threshold_speed_kmh = 13.0

    return AthleteProfile(
        athlete_id="athlete-test",
        declared_level="competitive",
        observed_level="competitive",
        physiological=physiological,
        tolerance=TrainingTolerance(
            learned_physiological_tolerance_score=70,
            learned_biomechanical_tolerance_score=80,
            learned_response_count=8 if with_metrics else 0,
        ),
        current_pain_or_injury=pain,
        history_activity_count=200 if with_metrics else 0,
        data_quality_score=90 if with_metrics else 0,
        profile_confidence_score=90 if with_metrics else 40,
    )


class TrainingProtocolSelectorTests(unittest.TestCase):
    """Validation du classement scientifique personnalisé."""

    def setUp(self) -> None:
        self.selector = TrainingProtocolSelector(
            build_default_training_protocol_registry()
        )

    def test_selects_three_protocols_for_compatible_profile(
        self,
    ) -> None:
        selections = self.selector.select(
            profile=build_profile(),
            phase="development",
            goal_distance_km=10.0,
            available_dynamic_metrics={"recovery_status"},
        )

        self.assertEqual(
            [
                item.protocol.protocol_id
                for item in selections
            ],
            [
                "mixed_threshold_vo2_v1",
                "hill_sprints_v1",
                "triangular_vo2_v1",
            ],
        )

    def test_excludes_intense_protocols_when_pain_is_active(
        self,
    ) -> None:
        selections = self.selector.select(
            profile=build_profile(pain=True),
            phase="development",
            goal_distance_km=10.0,
            available_dynamic_metrics={"recovery_status"},
        )

        self.assertEqual(selections, [])

    def test_reports_missing_metrics(self) -> None:
        selections = self.selector.select(
            profile=build_profile(with_metrics=False),
            phase="development",
            goal_distance_km=10.0,
        )

        mixed = next(
            item
            for item in selections
            if item.protocol.workout_type_key
            == "mixed_threshold_vo2"
        )

        self.assertEqual(
            mixed.missing_metrics,
            [
                "vma",
                "individual_threshold_speed",
                "recovery_status",
            ],
        )
        self.assertTrue(mixed.warnings)

    def test_uses_learned_session_type_tolerance(
        self,
    ) -> None:
        profile = build_profile()
        profile.tolerance.session_type_tolerance_scores[
            "hill_sprints"
        ] = 92

        selections = self.selector.select(
            profile=profile,
            phase="development",
            goal_distance_km=10.0,
            available_dynamic_metrics={"recovery_status"},
        )
        hills = next(
            item
            for item in selections
            if item.protocol.workout_type_key
            == "hill_sprints"
        )

        self.assertEqual(hills.tolerance_score, 92)

    def test_triangular_protocol_keeps_experimental_warning(
        self,
    ) -> None:
        selections = self.selector.select(
            profile=build_profile(),
            phase="development",
            goal_distance_km=10.0,
            available_dynamic_metrics={"recovery_status"},
        )
        triangular = next(
            item
            for item in selections
            if item.protocol.workout_type_key
            == "triangular_vo2"
        )

        self.assertIn(
            "Protocole Atlas encore expérimental.",
            triangular.warnings,
        )

    def test_filters_incompatible_goal_distance(self) -> None:
        selections = self.selector.select(
            profile=build_profile(),
            phase="development",
            goal_distance_km=21.1,
            available_dynamic_metrics={"recovery_status"},
        )

        self.assertEqual(
            {
                item.protocol.workout_type_key
                for item in selections
            },
            {
                "hill_sprints",
                "mixed_threshold_vo2",
            },
        )


if __name__ == "__main__":
    unittest.main()