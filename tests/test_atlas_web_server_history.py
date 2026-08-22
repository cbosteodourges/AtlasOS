import json
import tempfile
import unittest
from pathlib import Path

from tools.atlas_web_server import load_historical_workouts


class AtlasWebServerHistoryTests(unittest.TestCase):
    def test_loads_workouts_from_active_and_archived_programs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = {
                "weeks": [{"workouts": [{
                    "workout_id": "2026-08-22-hybrid",
                    "workout_date": "2026-08-22",
                    "title": "Sortie hybride",
                }]}]
            }
            archived = {
                "weeks": [{"workouts": [{
                    "workout_id": "2026-08-18-vo2",
                    "workout_date": "2026-08-18",
                    "title": "VO2max contrôlée",
                }]}]
            }
            (root / "training-program.json").write_text(
                json.dumps(active), encoding="utf-8"
            )
            (root / "training-program.backup.json").write_text(
                json.dumps(archived), encoding="utf-8"
            )

            workouts = load_historical_workouts(root)

            self.assertEqual(len(workouts), 2)
            restored = next(
                item for item in workouts
                if item["workout_date"] == "2026-08-18"
            )
            self.assertEqual(restored["title"], "VO2max contrôlée")
            self.assertTrue(restored["archived_program"])

    def test_ignores_corrupted_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "training-program.bad.json").write_text(
                "not-json", encoding="utf-8"
            )
            self.assertEqual(load_historical_workouts(root), [])


if __name__ == "__main__":
    unittest.main()
