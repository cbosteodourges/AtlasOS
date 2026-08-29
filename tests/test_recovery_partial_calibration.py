import unittest

from src.physiology.atlas_recovery_index import (
    _calibrate_partial_score,
    _score_sleep_duration,
)


class RecoveryCalibrationTests(unittest.TestCase):
    def test_sleep_deficit_is_not_scored_as_nearly_optimal(self):
        score = _score_sleep_duration(7 + 28 / 60, 8 + 2 / 60)
        self.assertLessEqual(score, 75)

    def test_missing_hrv_caps_optimistic_score_when_sleep_is_short(self):
        score = _calibrate_partial_score(
            90,
            74.5,
            34,
            hrv_available=False,
            nocturnal_hr_available=True,
        )
        self.assertEqual(score, 80)

    def test_complete_same_night_markers_preserve_raw_score(self):
        score = _calibrate_partial_score(
            90,
            74.5,
            34,
            hrv_available=True,
            nocturnal_hr_available=True,
        )
        self.assertEqual(score, 90)

    def test_missing_hrv_and_night_hr_never_looks_optimal(self):
        score = _calibrate_partial_score(
            94,
            91,
            12,
            hrv_available=False,
            nocturnal_hr_available=False,
        )
        self.assertEqual(score, 75)


if __name__ == "__main__":
    unittest.main()
