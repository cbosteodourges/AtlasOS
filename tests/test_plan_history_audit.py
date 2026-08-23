"""Tests du contrôle plan/historique."""

import unittest
from datetime import date

from src.training.plan_history_audit import audit_plan_history


class PlanHistoryAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.program = {
            "weeks": [{
                "workouts": [
                    {"workout_id": "run-1", "workout_date": "2026-08-18"},
                    {"workout_id": "run-2", "workout_date": "2026-08-20"},
                    {"workout_id": "bike", "workout_date": "2026-08-23", "optional": True},
                    {"workout_id": "future", "workout_date": "2026-08-25"},
                ]
            }]
        }

    def test_consistent_history(self) -> None:
        executions = [
            {"planned_workout": {"workout_id": "run-1"}, "match": {"matched": True}},
            {"planned_workout": {"workout_id": "run-2"}, "match": {"matched": True}},
        ]
        audit = audit_plan_history(self.program, executions, date(2026, 8, 23))
        self.assertTrue(audit.is_consistent)
        self.assertEqual(audit.completed_past_workouts, 2)

    def test_missing_past_workout_is_reported(self) -> None:
        audit = audit_plan_history(self.program, [], date(2026, 8, 23))
        self.assertEqual(audit.missing_past_workout_ids, ["run-1", "run-2"])

    def test_duplicate_and_orphan_are_reported(self) -> None:
        executions = [
            {"execution_id": "a", "planned_workout": {"id": "run-1"}, "match": {"matched": True}},
            {"execution_id": "b", "planned_workout": {"id": "run-1"}, "match": {"matched": True}},
            {"execution_id": "c", "planned_workout": {"id": "old-plan"}, "match": {"matched": True}},
        ]
        audit = audit_plan_history(self.program, executions, date(2026, 8, 23))
        self.assertEqual(audit.duplicate_execution_workout_ids, ["run-1"])
        self.assertEqual(audit.orphan_execution_ids, ["c"])

    def test_optional_workout_is_not_considered_missing(self) -> None:
        audit = audit_plan_history(self.program, [], date(2026, 8, 24))
        self.assertNotIn("bike", audit.missing_past_workout_ids)


if __name__ == "__main__":
    unittest.main()
