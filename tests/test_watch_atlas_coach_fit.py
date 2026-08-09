"""
Tests du surveillant automatique Atlas Coach.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.watch_atlas_coach_fit import (
    fit_snapshot,
    imported_count,
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

    def test_fit_snapshot_keeps_only_fit_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fit_file = root / "activity.fit"
            upper_fit_file = root / "SECOND.FIT"
            text_file = root / "notes.txt"

            fit_file.write_bytes(b"fit-data")
            upper_fit_file.write_bytes(b"other-fit-data")
            text_file.write_text(
                "ignore",
                encoding="utf-8",
            )

            snapshot = fit_snapshot(root)

            self.assertEqual(len(snapshot), 2)
            self.assertIn(fit_file.resolve(), snapshot)
            self.assertIn(upper_fit_file.resolve(), snapshot)
            self.assertNotIn(text_file.resolve(), snapshot)

    def test_fit_snapshot_accepts_missing_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"

            self.assertEqual(fit_snapshot(missing), {})


if __name__ == "__main__":
    unittest.main()