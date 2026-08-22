import json
import tempfile
import unittest
from pathlib import Path

from tools.atlas_web_server import (
    historical_completed_workouts_for_program,
    load_historical_workouts,
)


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

    def test_reintegrates_fit_execution_even_without_readable_archive(self):
        program = {
            "weeks": [{
                "start_date": "2026-08-17",
                "end_date": "2026-08-23",
                "workouts": [{
                    "workout_id": "2026-08-22-hybrid",
                    "workout_date": "2026-08-22",
                }],
            }]
        }
        executions = [{
            "activity_id": "fit-18",
            "start_time": "2026-08-18T20:12:00",
            "activity": {
                "sport": "running",
                "session_type": "vo2",
                "duration_minutes": 47,
                "distance_km": 8.09,
                "average_heart_rate_bpm": 134,
            },
            "analysis": {
                "session_type": "vo2",
                "blocks": [{
                    "block_type": "vma",
                    "duration_seconds": 180,
                    "distance_meters": 700,
                    "average_speed_kmh": 14,
                    "average_heart_rate_bpm": 158,
                }],
            },
            "workout_match": {"matched": False, "execution": {}},
        }]

        restored = historical_completed_workouts_for_program(
            program,
            executions=executions,
            archived_workouts=[],
        )

        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0]["workout_date"], "2026-08-18")
        self.assertEqual(restored[0]["title"], "VO₂max")
        self.assertEqual(restored[0]["planned_duration_minutes"], 47)
        self.assertEqual(restored[0]["planned_distance_km"], 8.09)
        self.assertEqual(restored[0]["blocks"][0]["block_type"], "vma")


if __name__ == "__main__":
    unittest.main()
