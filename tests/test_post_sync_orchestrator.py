import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.training.post_sync_orchestrator import PostSyncOrchestrator


class PostSyncOrchestratorTests(unittest.TestCase):
    def test_health_connect_activity_creates_detailed_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = {
                "athlete_snapshot": {"vma_kmh": 14},
                "weeks": [],
            }
            (root / "training-program.json").write_text(
                json.dumps(program),
                encoding="utf-8",
            )
            activity = SimpleNamespace(
                atlas_id="health_connect:exercise-1",
                provider="health_connect",
                source_ids={"health_connect": "exercise-1"},
            )
            record = {
                "activity_id": activity.atlas_id,
                "provider": "health_connect",
                "start_time": datetime(
                    2026, 8, 31, 17, 55, 13,
                    tzinfo=timezone.utc,
                ),
                "atlas_workout_match": {
                    "workout_id": "workout-1",
                    "matched": True,
                },
            }

            with (
                patch(
                    "scripts.sync_atlas_coach_pilot.build_record",
                    return_value=record,
                ),
                patch(
                    "scripts.sync_atlas_coach_pilot.confirm_matched_workouts",
                    return_value=1,
                ),
            ):
                count = PostSyncOrchestrator(
                    root
                )._refresh_activity_executions([activity])

            self.assertEqual(count, 1)
            executions = json.loads(
                (root / "atlas-coach-executions.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(executions), 1)
            self.assertEqual(
                executions[0]["activity_id"],
                activity.atlas_id,
            )
            self.assertEqual(
                executions[0]["start_time"],
                "2026-08-31T17:55:13+00:00",
            )

    def test_creates_assessment_and_never_overwrites_active_program(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = {"athlete_snapshot": {"vma_kmh": 14}, "weeks": [{"workouts": []}]}
            (root / "training-program.json").write_text(json.dumps(program), encoding="utf-8")
            end = datetime(2026, 8, 27, 6, tzinfo=timezone.utc)
            wellness = [{"type": "sleep", "source_id": "s1",
                         "start_time": (end - timedelta(hours=8)).isoformat(),
                         "end_time": end.isoformat(), "stages": []}]
            (root / "health-connect-wellness.json").write_text(json.dumps(wellness), encoding="utf-8")
            result = PostSyncOrchestrator(root).run("test")
            self.assertTrue(result["requires_user_validation"])
            self.assertTrue((root / "daily-sync-assessment.json").is_file())
            self.assertTrue((root / "nutrition-hydration-summary.json").is_file())
            self.assertTrue((root / "training-program-sync-proposal.json").is_file())
            self.assertEqual(json.loads((root / "training-program.json").read_text()), program)
            proposal = json.loads((root / "training-program-sync-proposal.json").read_text())
            self.assertTrue(proposal["active_program_unchanged"])
            self.assertIn("nutrition_hydration_context", proposal)


if __name__ == "__main__":
    unittest.main()
