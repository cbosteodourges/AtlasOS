import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.training.post_sync_orchestrator import PostSyncOrchestrator


class PostSyncOrchestratorTests(unittest.TestCase):
    def test_refresh_records_each_distinct_session_adjustment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "training-program.json").write_text(
                json.dumps({"athlete_snapshot": {}}),
                encoding="utf-8",
            )
            (root / "physiology-longitudinal.json").write_text(json.dumps({
                "current": {
                    "vo2_max": 51,
                    "vma_kmh": 14.57,
                    "sv1": {"speed_kmh": 10.25, "heart_rate_bpm": 136},
                    "sv2": {"speed_kmh": 12.75, "heart_rate_bpm": 153},
                },
                "history": [],
            }), encoding="utf-8")
            estimates = [
                {
                    "updated": True,
                    "decision": "maintain_reference",
                    "updated_at": "2026-09-02T08:00:00+00:00",
                    "session_assessment": {
                        "activity_id": "run-1",
                        "start_time": "2026-09-02T07:00:00+00:00",
                        "signals": {
                            "sv1": {
                                "speed_kmh": 10.35,
                                "heart_rate_bpm": 138,
                                "confidence": .85,
                            }
                        },
                    },
                },
                {
                    "updated": True,
                    "decision": "maintain_reference",
                    "updated_at": "2026-09-02T19:00:00+00:00",
                    "session_assessment": {
                        "activity_id": "run-2",
                        "start_time": "2026-09-02T18:00:00+00:00",
                        "signals": {
                            "sv2": {
                                "speed_kmh": 12.85,
                                "heart_rate_bpm": 155,
                                "confidence": .85,
                            }
                        },
                    },
                },
            ]

            with patch(
                "src.training.post_sync_orchestrator.ContinuousPhysiologyEstimator.estimate",
                side_effect=estimates,
            ):
                orchestrator = PostSyncOrchestrator(root)
                orchestrator.refresh_physiology(activities=[])
                orchestrator.refresh_physiology(activities=[])

            payload = json.loads(
                (root / "physiology-longitudinal.json").read_text(encoding="utf-8")
            )
            validated = [
                item for item in payload["history"]
                if item.get("schema") == "validated_profile_v1"
            ]
            # Les observations isolées ne créent plus deux faux profils
            # validés le même jour.
            self.assertEqual(len(validated), 1)
            self.assertEqual(
                [item["activity_id"] for item in validated],
                ["run-1"],
            )
            self.assertEqual(
                [item["timestamp"] for item in validated],
                [
                    "2026-09-02T07:00:00+00:00",
                ],
            )

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

    def test_keeps_single_session_threshold_as_pending_evidence(self):
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
        self.assertEqual(applied, [])
        self.assertEqual(profile["sv2"]["speed_kmh"], 12.75)
        self.assertEqual(profile["sv2"]["heart_rate_bpm"], 153)
        self.assertEqual(
            profile["pending_threshold_observations"]["activity_id"],
            "health_connect:threshold-1",
        )

        repeated, repeated_applied = PostSyncOrchestrator._auto_apply_physiology(
            profile, estimate
        )
        self.assertEqual(repeated_applied, [])
        self.assertEqual(repeated["sv2"]["heart_rate_bpm"], 153)

    def test_validates_two_concordant_weekly_threshold_states(self):
        profile = {
            "maximum_heart_rate_bpm": 170,
            "sv1": {"speed_kmh": 10.5, "heart_rate_bpm": 138},
            "sv2": {"speed_kmh": 12.65, "heart_rate_bpm": 153},
        }
        prior = {
            "week": "2026-S35",
            "states": {
                "sv2": {
                    "usable": True,
                    "direction": "progression",
                    "confidence": 78,
                }
            },
        }
        current = {
            "week": "2026-S36",
            "as_of": "2026-09-04",
            "states": {
                "sv2": {
                    "usable": True,
                    "direction": "progression",
                    "confidence": 84,
                    "projection": {
                        "speed_kmh": 12.87,
                        "heart_rate_bpm": 155,
                    },
                }
            },
        }

        updated, applied = PostSyncOrchestrator._apply_weekly_threshold_evolution(
            profile, current, [prior]
        )

        self.assertEqual(applied, ["sv2"])
        self.assertEqual(updated["sv2"]["speed_kmh"], 12.8)
        self.assertEqual(updated["sv2"]["heart_rate_bpm"], 155)
        self.assertEqual(updated["sv2"]["status"], "weekly_validated_threshold_v2")

    def test_same_week_never_counts_as_a_second_confirmation(self):
        profile = {"sv2": {"speed_kmh": 12.65, "heart_rate_bpm": 153}}
        current = {
            "week": "2026-S36",
            "as_of": "2026-09-04",
            "states": {"sv2": {
                "usable": True, "direction": "progression", "confidence": 90,
                "projection": {"speed_kmh": 12.9, "heart_rate_bpm": 155},
            }},
        }

        updated, applied = PostSyncOrchestrator._apply_weekly_threshold_evolution(
            profile, current, [current]
        )

        self.assertEqual(applied, [])
        self.assertEqual(updated, profile)

    def test_propagation_updates_snapshot_without_duplicating_workouts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = {
                "athlete_snapshot": {
                    "sv2": {"speed_kmh": 12.65, "heart_rate_bpm": 153},
                },
                "weeks": [{
                    "week_number": 1,
                    "workouts": [{
                        "workout_id": "threshold-1",
                        "workout_type": "threshold_sv2",
                        "blocks": [{
                            "block_type": "sv2",
                            "target": {
                                "speed_min_kmh": 12.4,
                                "speed_max_kmh": 12.7,
                                "heart_rate_min_bpm": 150,
                                "heart_rate_max_bpm": 158,
                            },
                        }],
                    }],
                }],
            }
            (root / "training-program.json").write_text(
                json.dumps(program), encoding="utf-8"
            )
            profile = {
                "sv2": {
                    "speed_kmh": 12.8,
                    "heart_rate_bpm": 155,
                    "status": "weekly_validated_threshold_v2",
                }
            }

            orchestrator = PostSyncOrchestrator(root)
            orchestrator._propagate_validated_physiology_to_program(
                program["athlete_snapshot"], profile, ["sv2"]
            )
            orchestrator._propagate_validated_physiology_to_program(
                profile, profile, ["sv2"]
            )

            updated = json.loads(
                (root / "training-program.json").read_text(encoding="utf-8")
            )
            self.assertEqual(updated["athlete_snapshot"]["sv2"]["speed_kmh"], 12.8)
            self.assertEqual(len(updated["weeks"][0]["workouts"]), 1)
            target = updated["weeks"][0]["workouts"][0]["blocks"][0]["target"]
            # Le second appel reçoit déjà le profil actualisé : il est
            # idempotent et ne décale pas une deuxième fois la cible.
            self.assertEqual(target["speed_min_kmh"], 12.5)
            self.assertEqual(target["heart_rate_min_bpm"], 152)
            self.assertEqual(
                updated["automatic_physiology_revision"]["schema"],
                "threshold_state_v2",
            )

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

    def test_fit_enrichment_replaces_prior_health_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "training-program.json").write_text(
                json.dumps({"athlete_snapshot": {"vma_kmh": 14}, "weeks": []}),
                encoding="utf-8",
            )
            (root / "atlas-coach-executions.json").write_text(
                json.dumps([{
                    "activity_id": "health_connect:exercise-1",
                    "provider": "health_connect",
                    "external_id": "exercise-1",
                    "atlas_workout_match": {"matched": True},
                }]),
                encoding="utf-8",
            )
            activity = SimpleNamespace(
                atlas_id="garmin:fit-1",
                provider="garmin",
                external_id="fit-1",
                source_ids={
                    "health_connect": "exercise-1",
                    "garmin": "fit-1",
                },
            )
            record = {
                "activity_id": "garmin:fit-1",
                "provider": "garmin",
                "external_id": "fit-1",
                "source_ids": activity.source_ids,
                "start_time": "2026-08-31T17:55:13+00:00",
                "atlas_workout_match": {"matched": True},
            }

            with (
                patch("scripts.sync_atlas_coach_pilot.build_record", return_value=record),
                patch("scripts.sync_atlas_coach_pilot.confirm_matched_workouts"),
            ):
                count = PostSyncOrchestrator(root)._refresh_activity_executions([activity])

            executions = json.loads(
                (root / "atlas-coach-executions.json").read_text(encoding="utf-8")
            )
            self.assertEqual(count, 1)
            self.assertEqual(len(executions), 1)
            self.assertEqual(executions[0]["activity_id"], "garmin:fit-1")

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
