import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools.atlas_web_server as server


class AtlasWebServerNutritionTests(unittest.TestCase):
    def test_founder_has_pilot_access(self):
        with patch.object(server, "load_subscription_entitlement", return_value={"tier": "founder_admin"}), \
             patch.object(server, "load_user_profile", return_value={}):
            access = server.nutrition_feature_access()
        self.assertTrue(access["enabled"])
        self.assertTrue(access["pilot"])

    def test_new_user_requires_explicit_feature(self):
        with patch.object(server, "load_subscription_entitlement", return_value={"tier": "annual"}), \
             patch.object(server, "load_user_profile", return_value={}):
            self.assertFalse(server.nutrition_feature_access()["enabled"])

    def test_manual_hydration_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(server, "NUTRITION_PATH", Path(directory) / "nutrition.json"), \
             patch.object(server, "nutrition_feature_access", return_value={"enabled": True}), \
             patch.object(server, "load_nutrition_hydration", return_value={"today": {}}):
            result = server.record_nutrition_hydration({"type": "hydration", "volume_ml": 500})
            self.assertEqual(result["record"]["volume_ml"], 500)
            self.assertTrue((Path(directory) / "nutrition.json").is_file())


if __name__ == "__main__":
    unittest.main()
