"""Tests du watcher Garmin Wellness Atlas."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIRECTORY = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

import watch_atlas_wellness  # noqa: E402


class WatchAtlasWellnessTests(unittest.TestCase):
    """Valide le déclenchement de la boucle rétroactive."""

    @patch("watch_atlas_wellness.subprocess.run")
    def test_runs_program_revision_after_wellness(
        self,
        mocked_run,
    ) -> None:
        mocked_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Statut : no_change",
            stderr="",
        )

        result = watch_atlas_wellness.run_revision()

        self.assertEqual(result.returncode, 0)
        command = mocked_run.call_args.args[0]
        self.assertIn("-X", command)
        self.assertIn("utf8", command)
        self.assertEqual(
            Path(command[-1]).name,
            "refresh_training_program_proposal.py",
        )
        self.assertTrue(mocked_run.call_args.kwargs["capture_output"])
        self.assertEqual(
            mocked_run.call_args.kwargs["encoding"],
            "utf-8",
        )


if __name__ == "__main__":
    unittest.main()