import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.training.post_sync_orchestrator import PostSyncOrchestrator


class PostSyncOrchestratorTests(unittest.TestCase):
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
