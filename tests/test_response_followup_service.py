import unittest
from datetime import date, datetime, timezone

from src.training.response_followup_service import TrainingResponseFollowupService
from src.training.session_models import (
    AdaptiveWorkout, BlockType, ExpectedTrainingResponse, TrainingBlock,
    WorkoutPriority, WorkoutType,
)


class ResponseFollowupServiceTests(unittest.TestCase):
    def test_builds_24_48_72_hour_learning_without_inventing_metrics(self):
        workout = AdaptiveWorkout(
            workout_id="sv2-1", workout_date=date(2026, 8, 30),
            workout_type=WorkoutType.THRESHOLD_SV2, title="SV2",
            objective="Seuil", priority=WorkoutPriority.KEY,
            blocks=[TrainingBlock(name="Travail", block_type=BlockType.WORK, duration_minutes=30)],
            expected_response=ExpectedTrainingResponse(
                physiological_load_0_100=70, biomechanical_load_0_100=55,
                recovery_min_hours=36, recovery_max_hours=48,
            ),
        )
        execution = {"workout_id": "sv2-1", "start_time": "2026-08-30T08:00:00Z"}
        recovery = [
            {"timestamp": "2026-08-30T07:00:00Z", "atlas_recovery_index": 70},
            {"timestamp": "2026-08-31T08:00:00Z", "atlas_recovery_index": 62, "sleep_score": 68},
            {"timestamp": "2026-09-01T08:00:00Z", "atlas_recovery_index": 72, "sleep_score": 82},
            {"timestamp": "2026-09-02T08:00:00Z", "atlas_recovery_index": 75},
        ]
        result = TrainingResponseFollowupService().build(
            [workout], [execution], recovery,
            [{"workout_id": "sv2-1", "fatigue_0_to_10": 3, "pain_0_to_10": 1}],
            now=datetime(2026, 9, 2, 10, tzinfo=timezone.utc),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual([item["hours_after_session"] for item in result[0]["checkpoints"]], [24, 48, 72])
        self.assertIsNone(result[0]["checkpoints"][0]["hrv_ms"])
        self.assertTrue(result[0]["next_decision_context"]["usable"])

    def test_waits_until_24_hours(self):
        service = TrainingResponseFollowupService()
        result = service.build([], [], [], [], now=datetime(2026, 9, 2, tzinfo=timezone.utc))
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
