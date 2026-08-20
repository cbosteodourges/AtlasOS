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

from scripts.sync_atlas_coach_pilot import confirm_matched_workouts


class AutomaticWorkoutConfirmationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
