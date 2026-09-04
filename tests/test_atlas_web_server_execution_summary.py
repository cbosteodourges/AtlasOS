import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tools.atlas_web_server import execution_summary, recalculate_execution


class AtlasWebServerExecutionSummaryTests(unittest.TestCase):
    def test_exposes_reconstructed_interval_details_to_browser(self):
        intervals = [{
            "duration_seconds": 180,
            "distance_meters": 681,
            "average_speed_kmh": 13.62,
            "recovery_duration_seconds": 79,
        }]
        private_execution = {
            "activity_id": "health-connect-2026-09-01",
            "atlas_workout_match": {
                "score_audit": {"execution": {"score": 95}},
                "execution": {
                    "planned_repetition_count": 5,
                    "completed_repetition_count": 6,
                    "interval_details": intervals,
                    "private_debug_payload": "must-not-leak",
                }
            },
        }

        summary = execution_summary(private_execution)
        browser_execution = summary["workout_match"]["execution"]

        self.assertEqual(browser_execution["interval_details"], intervals)
        self.assertEqual(browser_execution["planned_repetition_count"], 5)
        self.assertEqual(browser_execution["completed_repetition_count"], 6)
        self.assertNotIn("private_debug_payload", browser_execution)
        self.assertEqual(
            summary["workout_match"]["score_audit"]["execution"]["score"],
            95,
        )

    def test_recalculation_replaces_existing_activity_without_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            private_dir = Path(directory)
            (private_dir / "training-program.json").write_text(
                json.dumps({"weeks": []}), encoding="utf-8"
            )
            (private_dir / "atlas-coach-executions.json").write_text(
                json.dumps([{"activity_id": "activity-1", "external_id": "fit-1"}]),
                encoding="utf-8",
            )
            activity = SimpleNamespace(atlas_id="activity-1")
            refreshed = {
                "activity_id": "activity-1",
                "external_id": "fit-1",
                "start_time": "2026-09-03T18:00:00+00:00",
                "atlas_workout_match": {"matched": True},
            }
            store = MagicMock()
            store.load.return_value = [activity]

            with (
                patch("tools.atlas_web_server.ActivityStore", return_value=store),
                patch("tools.atlas_web_server.TrainingProgramLoader.load", return_value=[]),
                patch("scripts.sync_atlas_coach_pilot.load_analysis_profile", return_value=object()),
                patch("scripts.sync_atlas_coach_pilot.build_record", return_value=refreshed),
                patch("scripts.sync_atlas_coach_pilot.persist_restored_optional_workouts"),
                patch("scripts.sync_atlas_coach_pilot.confirm_matched_workouts"),
            ):
                recalculate_execution("activity-1", private_dir=private_dir)
                recalculate_execution("activity-1", private_dir=private_dir)

            saved = json.loads(
                (private_dir / "atlas-coach-executions.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["activity_id"], "activity-1")
            self.assertEqual(saved[0]["analysis_engine_version"], 1)
            self.assertIn("recalculated_at", saved[0])


if __name__ == "__main__":
    unittest.main()
