import json
import tempfile
import unittest
from pathlib import Path

from tools.atlas_web_server import (
    reschedule_program_request,
    undo_reschedule_request,
)


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

    def test_applied_reschedule_can_be_undone(self):
        original = json.loads(
            self.path.read_text(encoding="utf-8")
        )

        applied = reschedule_program_request({
            "workout_id": "vo2",
            "target_date": "2026-08-26",
            "apply": True,
        }, self.path)

        moved = json.loads(
            self.path.read_text(encoding="utf-8")
        )
        self.assertNotEqual(moved, original)

        result = undo_reschedule_request({
            "backup": applied["backup"],
        }, self.path)

        restored = json.loads(
            self.path.read_text(encoding="utf-8")
        )
        self.assertTrue(result["restored"])
        self.assertEqual(restored, original)
        self.assertTrue(
            (self.path.parent / result["undo_backup"]).is_file()
        )

    def test_server_and_calendar_expose_reschedule_route(self):
        root = Path(__file__).resolve().parents[1]
        server = (root / "tools" / "atlas_web_server.py").read_text(encoding="utf-8")
        calendar = (root / "app" / "js" / "atlas-training-calendar.js").read_text(encoding="utf-8")
        page = (root / "app" / "performance-running.html").read_text(encoding="utf-8")
        self.assertIn('"/api/atlas-coach/reschedule-workout"', server)
        self.assertIn('"/api/atlas-coach/undo-reschedule"', server)
        self.assertIn('data-reschedule-workout', calendar)
        self.assertIn('data-reschedule-confirm', calendar)
        self.assertIn('data-reschedule-undo', calendar)
        self.assertIn('CHOIX ÉQUILIBRÉ', calendar)
        self.assertIn('CHARGE ÉLEVÉE', calendar)
        self.assertIn('PRUDENCE ATLAS', calendar)
        self.assertIn('performance-running.css?v=77', page)
        self.assertIn('atlas-training-calendar.js?v=96', page)
        self.assertIn('compact-interval-details" open', calendar)
        self.assertIn('interval-recovery-detail', calendar)
        self.assertIn('execution-score-explanation', calendar)
        self.assertIn('pas votre niveau de forme', calendar)
        self.assertIn('const blockDuration = block =>', calendar)
        self.assertIn('distanceKm / representativeSpeed * 60', calendar)
        self.assertIn('personalZoneSpeed', calendar)
        self.assertIn('plannedDuration * Number(block.distance_meters) / totalDistance', calendar)
        self.assertIn('const optionalMetric = value =>', calendar)
        self.assertIn('Durées de récupération', calendar)
        self.assertIn('/api/atlas-coach/recalculate-execution', server)
        self.assertIn('data-recalculate-execution', calendar)
        self.assertIn('Comprendre le calcul des quatre scores', calendar)


if __name__ == "__main__":
    unittest.main()
