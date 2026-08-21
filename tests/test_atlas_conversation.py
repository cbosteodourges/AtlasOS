"""Tests du dialogue local et contextualisé Atlas."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tools.atlas_web_server import atlas_conversation


class AtlasConversationTests(unittest.TestCase):
    def _payload(self):
        return {
            "feeling": {"energy": 6, "fatigue": 3, "pain": 0},
            "preference": "planned",
            "note": "Jambes normales",
        }

    def test_explains_local_knowledge_and_missing_stale_wellness(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "tools.atlas_web_server.CONVERSATION_JOURNAL_PATH",
            Path(directory) / "journal.json",
        ), patch(
            "tools.atlas_web_server.load_wellness_history",
            return_value={"latest": {
                "day": "2026-01-01",
                "atlas_index": 95,
                "sleep_score": 90,
            }},
        ), patch(
            "tools.atlas_web_server.load_workout_contexts",
            return_value=[],
        ), patch(
            "tools.atlas_web_server._program_progress",
            return_value=None,
        ):
            result = atlas_conversation(self._payload())

        self.assertTrue(result["knowledge"]["local"])
        self.assertTrue(any(
            "plus de deux jours" in item
            for item in result["knowledge"]["does_not_know"]
        ))
        self.assertNotIn("Indice Atlas 95/100", result["assessment"]["evidence"])

    def test_uses_fresh_wellness_and_previous_post_workout_context(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "tools.atlas_web_server.CONVERSATION_JOURNAL_PATH",
            Path(directory) / "journal.json",
        ), patch(
            "tools.atlas_web_server.load_wellness_history",
            return_value={"latest": {
                "day": date.today().isoformat(),
                "atlas_index": 82,
                "sleep_score": 80,
                "sleep_recovery_score": 78,
                "hrv_last_night_ms": 50,
                "hrv_weekly_average_ms": 50,
            }},
        ), patch(
            "tools.atlas_web_server.load_workout_contexts",
            return_value=[{"fatigue_0_to_10": 7, "pain_0_to_10": 4}],
        ), patch(
            "tools.atlas_web_server._program_progress",
            return_value={"next_workout": {"title": "Endurance Z2", "date": date.today().isoformat()}},
        ):
            result = atlas_conversation(self._payload())

        self.assertIn("Indice Atlas 82/100", result["assessment"]["evidence"])
        self.assertTrue(any(
            "Dernière douleur" in item for item in result["assessment"]["evidence"]
        ))
        self.assertTrue(any(
            "dernier ressenti" in item.lower() for item in result["knowledge"]["knows"]
        ))


if __name__ == "__main__":
    unittest.main()
