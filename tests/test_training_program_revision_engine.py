"""Tests des propositions de révision du programme Atlas Coach."""

import unittest
from datetime import date

from src.training.program_revision_engine import (
    TrainingProgramRevisionEngine,
)


def build_program(
    future_title: str,
    *,
    future_duration: int = 55,
) -> dict:
    return {
        "weeks": [
            {
                "week_number": 1,
                "workouts": [
                    {
                        "workout_id": "past-session",
                        "workout_date": "2026-08-13",
                        "workout_type": "endurance_z2",
                        "title": "Séance déjà réalisée",
                        "planned_duration_minutes": 45,
                    },
                    {
                        "workout_id": "future-session",
                        "workout_date": "2026-08-18",
                        "workout_type": "vma_short",
                        "title": future_title,
                        "planned_duration_minutes": future_duration,
                    },
                ],
            }
        ]
    }


class TrainingProgramRevisionEngineTests(unittest.TestCase):
    """Valide la comparaison sûre du programme actif."""

    def test_proposes_only_future_changes(self) -> None:
        active = build_program("8 × 400 m VO₂max")
        candidate = build_program(
            "10 × 400 m VO₂max",
            future_duration=60,
        )
        candidate["weeks"][0]["workouts"][0]["title"] = (
            "Cette modification passée doit être ignorée"
        )

        proposal = TrainingProgramRevisionEngine().compare(
            active,
            candidate,
            as_of=date(2026, 8, 15),
        )

        self.assertEqual(proposal.status, "proposed")
        self.assertEqual(len(proposal.changes), 1)
        self.assertEqual(
            proposal.changes[0].workout_id,
            "future-session",
        )
        self.assertEqual(
            proposal.changes[0].changed_fields,
            ["planned_duration_minutes", "title"],
        )
        self.assertFalse(proposal.automatically_applied)
        self.assertTrue(proposal.requires_approval)

        payload = proposal.to_dict()
        self.assertEqual(payload["as_of"], "2026-08-15")
        self.assertEqual(
            payload["changes"][0]["workout_date"],
            "2026-08-18",
        )
        self.assertEqual(
            payload["changes"][0]["change_type"],
            "modified",
        )

    def test_reports_no_change_for_identical_programs(self) -> None:
        active = build_program("8 × 400 m VO₂max")

        proposal = TrainingProgramRevisionEngine().compare(
            active,
            build_program("8 × 400 m VO₂max"),
            as_of=date(2026, 8, 15),
        )

        self.assertEqual(proposal.status, "no_change")
        self.assertEqual(proposal.changes, [])
        self.assertFalse(proposal.requires_approval)


if __name__ == "__main__":
    unittest.main()