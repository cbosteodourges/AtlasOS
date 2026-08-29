import tempfile
import unittest

from src.connectors import HealthConnectBridge


class HealthConnectBridgeTests(unittest.TestCase):
    def test_pairing_code_is_single_use_and_token_allows_ingest(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = HealthConnectBridge(directory)
            code = bridge.create_pairing_code()
            token = bridge.pair(code, {"model": "Nothing Phone (2a)"})
            with self.assertRaises(ValueError):
                bridge.pair(code, {})
            result = bridge.ingest(token, {"activities": [{
                "source_id": "exercise-1", "type": "run",
                "start_time": "2026-08-26T18:00:00Z", "duration_seconds": 3200
            }], "wellness": [{"source_id": "sleep-1", "type": "sleep",
                                "start_time": "2026-08-25T22:00:00Z"}]})
            self.assertEqual(result["activities_total"], 1)
            self.assertEqual(result["wellness_total"], 1)

    def test_ingest_persists_record_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = HealthConnectBridge(directory)
            token = bridge.pair(bridge.create_pairing_code(), {"model": "test"})
            result = bridge.ingest(token, {
                "sync_schema_version": 2,
                "backfill_performed": True,
                "record_inventory": [{
                    "record_type": "Vo2MaxRecord", "count": 4,
                    "sources": ["com.garmin.android.apps.connectmobile"],
                }],
                "skipped_record_types": [],
            })
            self.assertEqual(result["record_types_available"], 1)
            inventory = bridge._read(bridge.inventory_path, {})
            self.assertTrue(inventory["backfill_performed"])
            self.assertEqual(inventory["record_types"][0]["count"], 4)

    def test_unknown_token_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PermissionError):
                HealthConnectBridge(directory).ingest("bad", {})

    def test_android_exercise_codes_are_normalized(self):
        expected = {
            "56": "running",
            "8": "cycling",
            "37": "hiking",
            "73": "swimming_open_water",
        }
        for code, activity_type in expected.items():
            with self.subTest(code=code):
                activity = HealthConnectBridge._activity({
                    "source_id": f"exercise-{code}",
                    "type": code,
                    "start_time": "2026-08-26T18:00:00Z",
                    "duration_seconds": 3600,
                })
                self.assertEqual(activity.activity_type, activity_type)
                self.assertEqual(
                    activity.raw_metadata["health_connect_exercise_type"],
                    code,
                )


if __name__ == "__main__":
    unittest.main()
