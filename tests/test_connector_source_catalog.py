"""Tests du catalogue des sources de données Atlas."""

import unittest

from src.connectors.source_catalog import (
    canonical_provider,
    get_source_capability,
    list_source_capabilities,
)


class SourceCatalogTests(unittest.TestCase):
    def test_all_user_facing_sources_are_declared(self) -> None:
        providers = [item.provider for item in list_source_capabilities()]
        self.assertEqual(
            providers,
            ["health_connect", "garmin", "polar", "suunto", "coros", "strava", "manual"],
        )

    def test_only_existing_local_paths_are_marked_operational(self) -> None:
        operational = {
            item.provider
            for item in list_source_capabilities()
            if item.connection_status == "operational"
        }
        self.assertEqual(operational, {"garmin", "manual"})

    def test_vendor_integrations_are_not_misrepresented(self) -> None:
        for provider in ("health_connect", "polar", "suunto", "coros", "strava"):
            capability = get_source_capability(provider)
            self.assertTrue(capability.requires_vendor_authorization)
            self.assertNotEqual(capability.connection_status, "operational")

    def test_aliases_are_canonicalized(self) -> None:
        self.assertEqual(canonical_provider("Health Connect"), "health_connect")
        self.assertEqual(canonical_provider("Polar Flow"), "polar")
        self.assertEqual(canonical_provider("Sans montre"), "manual")

    def test_manual_mode_preserves_wellness_without_watch(self) -> None:
        capability = get_source_capability("no watch")
        self.assertTrue(capability.wellness_supported)
        self.assertTrue(capability.incremental_supported)


if __name__ == "__main__":
    unittest.main()
