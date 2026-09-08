import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.audit_fit_archive import audit_archive, discover_fit_files


class FitArchiveAuditTests(unittest.TestCase):
    def test_discovers_fit_files_recursively_and_reports_physiology_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "2017" / "running"
            nested.mkdir(parents=True)
            fit_path = nested / "activity.FIT"
            fit_path.write_bytes(b"fit")
            (nested / "notes.txt").write_text("ignore", encoding="utf-8")

            def decode(path):
                self.assertEqual(path, fit_path)
                return ({
                    "session_mesgs": [{
                        "sport": "running",
                        "start_time": datetime(2017, 5, 1, tzinfo=timezone.utc),
                        "total_training_effect": 3.4,
                    }],
                    "record_mesgs": [{"heart_rate": 150}],
                    "physiological_metrics_mesgs": [{"vo2_max": 52.1}],
                }, [])

            report = audit_archive(root, decoder=decode)

            self.assertEqual(discover_fit_files(root), [fit_path])
            self.assertEqual(report["file_count"], 1)
            self.assertEqual(report["decoded_file_count"], 1)
            self.assertEqual(report["first_activity_day"], "2017-05-01")
            self.assertEqual(report["sports"], {"running": 1})
            self.assertIn(
                "physiological_metrics_mesgs.vo2_max",
                report["physiology_fields"],
            )
            self.assertEqual(
                report["physiology_fields"]["physiological_metrics_mesgs.vo2_max"]["examples"],
                [52.1],
            )


if __name__ == "__main__":
    unittest.main()
