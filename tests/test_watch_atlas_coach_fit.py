"""
Tests du surveillant automatique Atlas Coach.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.watch_atlas_coach_fit import (
    changed_fit_paths,
    fit_snapshot,
    imported_count,
    run_feedback_cycle,
)


class AtlasCoachFitWatcherTests(unittest.TestCase):
    """Valide la détection locale des fichiers FIT."""

    def test_imported_count_reads_sync_summary(self) -> None:
        output = (
            "Synchronisation Atlas Coach terminée : "
            "2 nouvelle(s) activité(s).\n"
            "Correspondances Atlas fiables : 1/2."
        )

        self.assertEqual(imported_count(output), 2)

    def test_imported_count_returns_zero_without_summary(
        self,
    ) -> None:
        self.assertEqual(
            imported_count("Aucune donnée disponible."),
            0,
        )

    def test_fit_snapshot_keeps_fit_and_zip_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fit_file = root / "activity.fit"
            upper_fit_file = root / "SECOND.FIT"
            zip_file = root / "activity.zip"
            text_file = root / "notes.txt"

            fit_file.write_bytes(b"fit-data")
            upper_fit_file.write_bytes(b"other-fit-data")
            zip_file.write_bytes(b"garmin-archive")
            text_file.write_text(
                "ignore",
                encoding="utf-8",
            )

            snapshot = fit_snapshot(root)

            self.assertEqual(len(snapshot), 3)
            self.assertIn(fit_file.resolve(), snapshot)
            self.assertIn(upper_fit_file.resolve(), snapshot)
            self.assertIn(zip_file.resolve(), snapshot)
            self.assertNotIn(text_file.resolve(), snapshot)

    def test_fit_snapshot_accepts_missing_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"

            self.assertEqual(fit_snapshot(missing), {})

    def test_incomplete_file_is_retried_without_signature_change(self) -> None:
        path = Path("activity.fit")
        signature = (1024, 123456)

        changed = changed_fit_paths(
            {path: signature},
            {path: signature},
            {path},
        )

        self.assertEqual(changed, [path])


    @patch("scripts.watch_atlas_coach_fit.subprocess.run")
    def test_feedback_cycle_runs_fusion_then_revision(
        self,
        mocked_run,
    ) -> None:
        mocked_run.side_effect = [
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Fusion terminée",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Statut : no_change",
                stderr="",
            ),
        ]

        fusion, revision = run_feedback_cycle()

        self.assertEqual(fusion.returncode, 0)
        self.assertIsNotNone(revision)
        self.assertEqual(mocked_run.call_count, 2)
        commands = [
            call.args[0]
            for call in mocked_run.call_args_list
        ]
        self.assertEqual(
            Path(commands[0][-1]).name,
            "analyze_training_history_fusion.py",
        )
        self.assertEqual(
            Path(commands[1][-1]).name,
            "refresh_training_program_proposal.py",
        )

    @patch("scripts.watch_atlas_coach_fit.subprocess.run")
    def test_feedback_cycle_stops_when_fusion_fails(
        self,
        mocked_run,
    ) -> None:
        mocked_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Fusion impossible",
        )

        fusion, revision = run_feedback_cycle()

        self.assertEqual(fusion.returncode, 1)
        self.assertIsNone(revision)
        self.assertEqual(mocked_run.call_count, 1)

if __name__ == "__main__":
    unittest.main()
