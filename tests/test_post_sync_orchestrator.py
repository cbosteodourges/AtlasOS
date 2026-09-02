import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.training.post_sync_orchestrator import PostSyncOrchestrator


class PostSyncOrchestratorTests(unittest.TestCase):
    def test_threshold_reference_replaces_weaker_longitudinal_sv2_hr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "training-program.json").write_text(json.dumps({
                "athlete_snapshot": {
                    "sv2": {
                        "speed_kmh": 12.9,
                        "heart_rate_bpm": 151,
                        "status": "longitudinal_estimate",
                    },
                }
            }), encoding="utf-8")
            (root / "physiology-longitudinal.json").write_text(json.dumps({
                "current": {
                    "sv2": {
                        "speed_kmh": 12.9,
                        "heart_rate_bpm": 151,
                        "status": "longitudinal_estimate",
                    }
                }
            }), encoding="utf-8")
            (root / "athlete-profile.json").write_text(json.dumps({
                "physiological": {"threshold_heart_rate_bpm": 160}
            }), encoding="utf-8")

            profile = PostSyncOrchestrator(root)._current_physiology()

            self.assertEqual(profile["sv2"]["heart_rate_bpm"], 160)
            self.assertEqual(
                profile["sv2"]["status"],
                "validated_threshold_reference",
            )

    def test_threshold_reference_preserves_session_adjusted_sv2_hr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "training-program.json").write_text(json.dumps({
                "athlete_snapshot": {},
            }), encoding="utf-8")
            (root / "physiology-longitudinal.json").write_text(json.dumps({
                "current": {
                    "sv2": {
                        "speed_kmh": 12.85,
                        "heart_rate_bpm": 155,
                        "status": "session_adjusted_estimate",
                    }
                }
            }), encoding="utf-8")
            (root / "athlete-profile.json").write_text(json.dumps({
                "physiological": {"threshold_heart_rate_bpm": 153}
            }), encoding="utf-8")

            profile = PostSyncOrchestrator(root)._current_physiology()

            self.assertEqual(profile["sv2"]["heart_rate_bpm"], 155)
            self.assertEqual(
                profile["sv2"]["status"],
                "session_adjusted_estimate",
            )

    def test_auto_applies_only_bounded_fast_vo2_gain(self):
        previous = {
            "vo2_max": 50,
            "vma_kmh": 14,
            "sv1": {"speed_kmh": 10.5},
            "sv2": {"speed_kmh": 12.9},
        }
        estimate = {
            "decision": "increase_candidate",
            "vo2_max": 51,
            "vma_kmh": 14.2,
            "sv1": {"speed_kmh": 10.7},
            "sv2": {"speed_kmh": 13.1},
            "updated_at": "2026-09-02T08:00:00+00:00",
            "observed": {"fast_vo2_signal": True},
        }

        profile, applied = PostSyncOrchestrator._auto_apply_physiology(
            previous, estimate
        )

        self.assertEqual(applied, ["vo2_max"])
        self.assertEqual(profile["vo2_max"], 51)
        self.assertEqual(profile["vma_kmh"], 14)
        self.assertEqual(profile["sv1"]["speed_kmh"], 10.5)
        self.assertEqual(profile["sv2"]["speed_kmh"], 12.9)

    def test_auto_applies_bounded_threshold_signal_once(self):
        previous = {
            "vo2_max": 51,
            "vma_kmh": 14.57,
            "sv1": {"speed_kmh": 10.35, "heart_rate_bpm": 138},
            "sv2": {"speed_kmh": 12.75, "heart_rate_bpm": 153},
        }
        estimate = {
            "decision": "maintain_reference",
            "vo2_max": 51,
            "updated_at": "2026-09-02T12:00:00+00:00",
            "observed": {},
            "session_assessment": {
                "activity_id": "health_connect:threshold-1",
                "signals": {
                    "sv2": {
                        "speed_kmh": 12.9,
                        "heart_rate_bpm": 159,
                        "confidence": .85,
                        "evidence": "Palier soutenu proche du second seuil.",
                    }
                },
            },
        }

        profile, applied = PostSyncOrchestrator._auto_apply_physiology(
            previous, estimate
        )
        self.assertEqual(applied, ["sv2"])
        self.assertEqual(profile["sv2"]["speed_kmh"], 12.85)
        self.assertEqual(profile["sv2"]["heart_rate_bpm"], 155)

        repeated, repeated_applied = PostSyncOrchestrator._auto_apply_physiology(
            profile, estimate
        )
        self.assertEqual(repeated_applied, [])
        self.assertEqual(repeated["sv2"]["heart_rate_bpm"], 155)

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

    def test_health_connect_wellness_has_priority_over_garmin_cache(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            health_value = {
                "type": "resting_heart_rate",
                "source_id": "health-rhr",
                "start_time": "2026-08-31T06:00:00+00:00",
                "value": 42,
            }
            (root / "health-connect-wellness.json").write_text(
                json.dumps([health_value]),
                encoding="utf-8",
            )
            cache = {
                "archives": {
                    "2026-08-31": {
                        "snapshot": {
                            "day": "2026-08-31",
                            "resting_heart_rate_bpm": 50,
                        }
                    }
                }
            }
            (
                root / "garmin-wellness-snapshot-cache.json"
            ).write_text(
                json.dumps(cache),
                encoding="utf-8",
            )

            merged = PostSyncOrchestrator(root)._merged_wellness()
            resting = [
                item
                for item in merged
                if item.get("type") == "resting_heart_rate"
                and str(item.get("start_time"))[:10]
                == "2026-08-31"
            ]

            self.assertEqual(len(resting), 1)
            self.assertEqual(resting[0]["value"], 42)
            self.assertEqual(
                resting[0]["source_id"],
                "health-rhr",
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
