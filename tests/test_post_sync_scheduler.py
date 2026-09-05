import tempfile
import threading
import unittest
from unittest.mock import patch

from src.training.post_sync_scheduler import post_sync_status, schedule_post_sync


class PostSyncSchedulerTests(unittest.TestCase):
    def test_second_request_is_coalesced_while_processing(self):
        started = threading.Event()
        release = threading.Event()
        runs = []

        def run(_instance, source):
            runs.append(source)
            started.set()
            release.wait(2)
            return {}

        with tempfile.TemporaryDirectory() as directory, patch(
            "src.training.post_sync_orchestrator.PostSyncOrchestrator.run",
            autospec=True,
            side_effect=run,
        ):
            first = schedule_post_sync(directory, "health_connect")
            self.assertEqual(first["status"], "processing")
            self.assertTrue(started.wait(1))
            second = schedule_post_sync(directory, "health_connect")
            self.assertTrue(second["pending"])
            release.set()

            for _ in range(100):
                if post_sync_status(directory)["status"] == "complete":
                    break
                threading.Event().wait(0.01)

            self.assertEqual(post_sync_status(directory)["status"], "complete")
            self.assertEqual(runs, ["health_connect", "health_connect"])


if __name__ == "__main__":
    unittest.main()
