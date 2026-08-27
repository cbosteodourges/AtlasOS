import json
import tempfile
import unittest
from pathlib import Path

from tools.atlas_web_server import reschedule_program_request


class AtlasWebServerRescheduleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "training-program.json"
        self.program = {"weeks": [{"week_number": 1, "workouts": [
            {"workout_id": "vo2", "workout_date": "2026-08-25", "title": "8 × 400 m", "workout_type": "vo2max"},
            {"workout_id": "threshold", "workout_date": "2026-08-27", "title": "SV2", "workout_type": "threshold"},
        ]}]}
        self.path.write_text(json.dumps(self.program), encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def test_preview_does_not_modify_program(self):
        result = reschedule_program_request({
            "workout_id": "vo2", "target_date": "2026-08-26",
        }, self.path)
        self.assertFalse(result["applied"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(json.loads(self.path.read_text()), self.program)

    def test_apply_writes_program_and_backup(self):
        result = reschedule_program_request({
            "workout_id": "vo2", "target_date": "2026-08-26", "apply": True,
        }, self.path)
        self.assertTrue(result["applied"])
        self.assertTrue((self.path.parent / result["backup"]).is_file())
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        moved = next(
            item for item in saved["weeks"][0]["workouts"]
            if item["workout_id"] == "vo2"
        )
        self.assertEqual(moved["workout_date"], "2026-08-26")

    def test_server_and_calendar_expose_reschedule_route(self):
        root = Path(__file__).resolve().parents[1]
        server = (root / "tools" / "atlas_web_server.py").read_text(encoding="utf-8")
        calendar = (root / "app" / "js" / "atlas-training-calendar.js").read_text(encoding="utf-8")
        page = (root / "app" / "performance-running.html").read_text(encoding="utf-8")
        self.assertIn('"/api/atlas-coach/reschedule-workout"', server)
        self.assertIn('data-reschedule-workout', calendar)
        self.assertIn('data-reschedule-confirm', calendar)
        self.assertIn('performance-running.css?v=61', page)


if __name__ == "__main__":
    unittest.main()
