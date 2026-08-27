"""Tests de la finalisation automatique des séances Atlas Coach."""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

garmin_fit_sdk = types.ModuleType("garmin_fit_sdk")
garmin_fit_sdk.Decoder = object
garmin_fit_sdk.Stream = object
sys.modules.setdefault("garmin_fit_sdk", garmin_fit_sdk)

from scripts.sync_atlas_coach_pilot import (
    confirm_matched_workouts,
    detected_optional_threshold_workout,
    load_concatenated_json_lists,
    load_optional_workouts,
    persist_restored_optional_workouts,
    fit_file_signature,
    load_fit_index,
    save_fit_index,
    select_fit_files,
)
from src.performance import AthleteProfile, PhysiologicalReferences
from src.training import TrainingProgramLoader


class AutomaticWorkoutConfirmationTests(unittest.TestCase):

    def test_incremental_fit_index_selects_only_new_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_fit = root / "old.fit"
            new_fit = root / "new.FIT"
            old_fit.write_bytes(b"old")
            new_fit.write_bytes(b"new")
            index = root / "fit-index.json"
            save_fit_index(index, {fit_file_signature(old_fit)})

            selected, signatures, bootstrapped = select_fit_files(
                str(root),
                str(index),
                str(root / "history.json"),
            )

            self.assertEqual(selected, [new_fit])
            self.assertIn(fit_file_signature(old_fit), signatures)
            self.assertFalse(bootstrapped)

    def test_existing_history_bootstraps_fit_index_without_redecode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fit_path = root / "already-treated.fit"
            fit_path.write_bytes(b"fit")
            history = root / "history.json"
            history.write_text("[]", encoding="utf-8")

            selected, signatures, bootstrapped = select_fit_files(
                str(root),
                str(root / "missing-index.json"),
                str(history),
            )

            self.assertEqual(selected, [])
            self.assertIn(fit_file_signature(fit_path), signatures)
            self.assertTrue(bootstrapped)

    def test_force_keeps_all_fit_files_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fit_path = root / "activity.fit"
            fit_path.write_bytes(b"fit")
            index = root / "fit-index.json"
            save_fit_index(index, {fit_file_signature(fit_path)})

            selected, _, _ = select_fit_files(
                str(root),
                str(index),
                str(root / "history.json"),
                force=True,
            )

            self.assertEqual(selected, [fit_path])
            self.assertEqual(
                load_fit_index(str(index)),
                {fit_file_signature(fit_path)},
            )

    def test_recovers_concatenated_optional_workout_lists(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "optional.json"
            source.write_text(
                json.dumps([{
                    "workout_id": "optional-1",
                    "title": "Ancienne version",
                }])
                + "\n"
                + json.dumps([{
                    "workout_id": "optional-1",
                    "title": "Dernière version",
                }, {
                    "workout_id": "optional-2",
                    "title": "Deuxième séance",
                }]),
                encoding="utf-8",
            )

            workouts = load_concatenated_json_lists(source)

            self.assertEqual(len(workouts), 2)
            self.assertEqual(workouts[0]["title"], "Dernière version")
            self.assertEqual(workouts[1]["workout_id"], "optional-2")
            self.assertEqual(
                len(json.loads(source.read_text(encoding="utf-8"))),
                2,
            )

    def test_discards_corrupt_trailing_fragment_after_valid_list(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "optional.json"
            source.write_text(
                json.dumps([{
                    "workout_id": "optional-valid",
                    "title": "Séance conservée",
                }]) + "\n]fragment incomplet",
                encoding="utf-8",
            )

            workouts = load_concatenated_json_lists(source)

            self.assertEqual(len(workouts), 1)
            self.assertEqual(workouts[0]["workout_id"], "optional-valid")
            self.assertEqual(
                json.loads(source.read_text(encoding="utf-8")),
                workouts,
            )
            backups = list(
                Path(directory).glob("optional.corrupt-backup-*.json")
            )
            self.assertEqual(len(backups), 1)
            self.assertIn(
                "fragment incomplet",
                backups[0].read_text(encoding="utf-8"),
            )

    def test_reliable_match_marks_workout_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "decisions.json"
            added = confirm_matched_workouts(
                [{
                    "activity_id": "garmin:123",
                    "atlas_workout_match": {
                        "workout_id": "threshold-2026-08-20",
                        "matched": True,
                    },
                }],
                destination,
            )

            self.assertEqual(added, 1)
            decisions = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(decisions[0]["status"], "completed")
            self.assertEqual(decisions[0]["activity_id"], "garmin:123")

    def test_unreliable_match_is_not_confirmed(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "decisions.json"
            added = confirm_matched_workouts(
                [{
                    "activity_id": "garmin:456",
                    "atlas_workout_match": {
                        "workout_id": "threshold-2026-08-20",
                        "matched": False,
                    },
                }],
                destination,
            )

            self.assertEqual(added, 0)
            self.assertFalse(destination.exists())

    def test_ui_block_names_are_normalized_for_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "optional.json"
            source.write_text(json.dumps([{
                "workout_id": "2026-08-20-optional-threshold_run",
                "workout_date": "2026-08-20",
                "workout_type": "threshold_run",
                "title": "Seuil SV2",
                "objective": "Test",
                "priority": "optional",
                "blocks": [{
                    "name": "3 × 8 min au SV2",
                    "block_type": "interval",
                    "duration_minutes": 8,
                    "repetitions": 3,
                }],
            }]), encoding="utf-8")

            workouts = load_optional_workouts(
                source,
                TrainingProgramLoader(),
            )

            self.assertEqual(workouts[0].workout_type.value, "threshold_sv2")
            self.assertEqual(workouts[0].blocks[0].block_type.value, "work")

    def test_stretching_optional_workout_is_loaded_as_mobility(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "optional.json"
            source.write_text(json.dumps([{
                "workout_id": "2026-08-27-optional-stretching",
                "workout_date": "2026-08-27",
                "workout_type": "stretching",
                "title": "Étirements",
                "objective": "Récupération",
                "priority": "optional",
                "sport": "mobility",
                "blocks": [{
                    "name": "Étirements doux",
                    "block_type": "stretching",
                    "duration_minutes": 15,
                }],
            }]), encoding="utf-8")

            workouts = load_optional_workouts(
                source,
                TrainingProgramLoader(),
            )

            self.assertEqual(workouts[0].workout_type.value, "mobility")
            self.assertEqual(workouts[0].blocks[0].block_type.value, "mobility")

    def test_detected_sv2_restores_exact_optional_workout_id(self):
        longitudinal = types.SimpleNamespace(
            activity_type="running",
            start_time=__import__("datetime").datetime(2026, 8, 20, 20, 52),
        )
        analysis = types.SimpleNamespace(
            dominant_work_type="sv2",
            work_duration_seconds=1975.7,
            blocks=[
                types.SimpleNamespace(
                    block_type="z2",
                    duration_seconds=535.7,
                ),
                types.SimpleNamespace(
                    block_type="sv2",
                    duration_seconds=480,
                ),
                types.SimpleNamespace(
                    block_type="sv2",
                    duration_seconds=480,
                ),
                types.SimpleNamespace(
                    block_type="sv2",
                    duration_seconds=480,
                ),
            ],
        )
        profile = AthleteProfile(
            athlete_id="test",
            declared_level="test",
            observed_level="test",
            physiological=PhysiologicalReferences(
                maximum_heart_rate_bpm=170,
                vma_kmh=14,
            ),
        )

        workout = detected_optional_threshold_workout(
            longitudinal,
            analysis,
            TrainingProgramLoader(),
            profile,
        )

        self.assertEqual(
            workout.workout_id,
            "2026-08-20-optional-threshold_run",
        )
        self.assertEqual(workout.blocks[1].repetitions, 3)
        self.assertEqual(workout.blocks[1].duration_minutes, 8)

    def test_restored_workout_is_persisted_for_calendar(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "optional.json"
            count = persist_restored_optional_workouts([{
                "restored_optional_workout": {
                    "workout_id": "2026-08-20-optional-threshold_run",
                    "workout_date": "2026-08-20",
                    "title": "Seuil SV2",
                },
            }], destination)

            self.assertEqual(count, 1)
            saved = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["title"], "Seuil SV2")


if __name__ == "__main__":
    unittest.main()
