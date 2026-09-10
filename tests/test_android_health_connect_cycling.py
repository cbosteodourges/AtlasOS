import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android" / "atlas-connect" / "app" / "src" / "main"


class AndroidHealthConnectCyclingTests(unittest.TestCase):
    def test_background_sync_uses_workmanager_minimum_period(self):
        scheduler = (
            ANDROID / "java" / "fr" / "atlasos" / "connect" / "AtlasAutoSync.kt"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "PeriodicWorkRequestBuilder<AtlasSyncWorker>(15, TimeUnit.MINUTES)",
            scheduler,
        )

    def test_requests_and_serializes_cycling_cadence(self):
        manifest = (ANDROID / "AndroidManifest.xml").read_text(encoding="utf-8")
        sync = (
            ANDROID / "java" / "fr" / "atlasos" / "connect" / "HealthSync.kt"
        ).read_text(encoding="utf-8")
        delta = (
            ANDROID / "java" / "fr" / "atlasos" / "connect" / "HealthDeltaSync.kt"
        ).read_text(encoding="utf-8")
        changes = (
            ANDROID / "java" / "fr" / "atlasos" / "connect" / "HealthChangeSync.kt"
        ).read_text(encoding="utf-8")

        self.assertIn("READ_CYCLING_PEDALING_CADENCE", manifest)
        self.assertIn("CyclingPedalingCadenceRecord", sync)
        self.assertIn("it.revolutionsPerMinute", sync)
        self.assertIn("CyclingPedalingCadenceRecord", delta)
        self.assertIn("CyclingPedalingCadenceRecord::class", changes)
        self.assertIn("SYNC_SCHEMA_VERSION = 9", sync)


if __name__ == "__main__":
    unittest.main()
