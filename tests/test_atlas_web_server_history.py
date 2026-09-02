import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.atlas_web_server import (
    historical_completed_workouts_for_program,
    load_historical_workouts,
    load_physiology_history,
    load_physiological_reference,
    load_user_objectives,
    load_user_profile,
    save_user_objectives,
    save_user_profile,
)


class AtlasWebServerHistoryTests(unittest.TestCase):
    def test_physiology_history_keeps_multiple_adjustments_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "atlas-data" / "private"
            private.mkdir(parents=True)
            (private / "physiology-longitudinal.json").write_text(json.dumps({
                "history": [
                    {
                        "day": "2026-09-02",
                        "timestamp": "2026-09-02T07:00:00+00:00",
                        "activity_id": "run-1",
                        "schema": "validated_profile_v1",
                        "vo2_max": 51,
                        "auto_applied": ["vo2_max"],
                    },
                    {
                        "day": "2026-09-02",
                        "timestamp": "2026-09-02T18:00:00+00:00",
                        "activity_id": "run-2",
                        "schema": "validated_profile_v1",
                        "vo2_max": 51.3,
                        "auto_applied": ["vo2_max", "vma_kmh"],
                    },
                ]
            }), encoding="utf-8")

            with patch("tools.atlas_web_server.ROOT", root):
                history = load_physiology_history()

            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["activity_id"], "run-1")
            self.assertEqual(history[1]["vo2_max"], 51.3)
            self.assertEqual(
                history[1]["adjusted_metrics"],
                ["vo2_max", "vma_kmh"],
            )

    def test_longitudinal_profile_overrides_program_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "atlas-data" / "private"
            private.mkdir(parents=True)
            program_path = private / "training-program.json"
            program_path.write_text(json.dumps({
                "athlete_snapshot": {
                    "vo2_max": 50.3,
                    "sv2": {"speed_kmh": 12.75, "heart_rate_bpm": 151},
                }
            }), encoding="utf-8")
            (private / "physiology-longitudinal.json").write_text(json.dumps({
                "current": {
                    "vo2_max": 51,
                    "sv2": {"speed_kmh": 12.9, "heart_rate_bpm": 160},
                }
            }), encoding="utf-8")

            with (
                patch("tools.atlas_web_server.ROOT", root),
                patch("tools.atlas_web_server.PROGRAM_PATH", program_path),
            ):
                physiology = load_physiological_reference()

            self.assertEqual(physiology["vo2_max"], 51)
            self.assertEqual(physiology["sv2_speed_kmh"], 12.9)
            self.assertEqual(physiology["sv2_heart_rate_bpm"], 160)

    def test_profile_is_persisted_outside_browser_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            saved = save_user_profile({"vma": 14.57}, path)
            loaded = load_user_profile(path)

            self.assertEqual(loaded["vma"], 14.57)
            self.assertIn("updatedAt", saved)

    def test_objectives_are_persisted_and_invalid_items_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "objectives.json"
            saved = save_user_objectives([
                {"name": "Semi de Lille", "date": "2026-10-25"},
                {"name": "Sans date"},
            ], path)

            self.assertEqual(len(saved), 1)
            self.assertEqual(load_user_objectives(path)[0]["name"], "Semi de Lille")

    def test_objective_is_rebuilt_from_active_program_when_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing-objectives.json"
            program = {
                "goal": {
                    "name": "Semi-marathon de Lille",
                    "event_date": "2026-10-25",
                    "distance_km": 21.1,
                    "target_time_minutes": 109,
                }
            }
            with patch(
                "tools.atlas_web_server.load_authorized_training_program",
                return_value=program,
            ):
                objectives = load_user_objectives(path)

            self.assertEqual(objectives[0]["type"], "half")
            self.assertEqual(objectives[0]["targetTime"], "01:49:00")

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
