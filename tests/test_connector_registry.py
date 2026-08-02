"""Tests automatisés du registre des connecteurs ATLAS OS."""

import unittest

from src.connectors import ConnectorRegistry, DemoConnector


class ConnectorRegistryTests(unittest.TestCase):
    """Vérifie l'enregistrement et la recherche des connecteurs."""

    def setUp(self) -> None:
        self.registry = ConnectorRegistry()
        self.connector = DemoConnector()

    def test_register_and_get_connector(self) -> None:
        self.registry.register(self.connector)

        registered = self.registry.get("demo")

        self.assertIs(registered, self.connector)
        self.assertTrue(self.registry.contains("demo"))
        self.assertEqual(self.registry.providers(), ["demo"])

    def test_provider_lookup_is_case_insensitive(self) -> None:
        self.registry.register(self.connector)

        registered = self.registry.get("DEMO")

        self.assertIs(registered, self.connector)

    def test_duplicate_provider_is_rejected(self) -> None:
        self.registry.register(self.connector)

        with self.assertRaises(ValueError):
            self.registry.register(DemoConnector())

    def test_connector_can_be_replaced(self) -> None:
        self.registry.register(self.connector)
        replacement = DemoConnector()

        self.registry.register(replacement, replace=True)

        self.assertIs(self.registry.get("demo"), replacement)

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.registry.get("garmin")

    def test_unregister_connector(self) -> None:
        self.registry.register(self.connector)

        self.registry.unregister("demo")

        self.assertFalse(self.registry.contains("demo"))
        self.assertEqual(self.registry.providers(), [])


if __name__ == "__main__":
    unittest.main()