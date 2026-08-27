import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from src.connectors import StravaOAuthService


class StravaOAuthTests(unittest.TestCase):
    def service(self, directory):
        return StravaOAuthService(directory, client_id="123", client_secret="secret",
            redirect_uri="http://localhost/callback")

    def test_authorization_url_records_temporary_state(self):
        with tempfile.TemporaryDirectory() as directory:
            service = self.service(directory)
            url = service.authorization_url()
            self.assertIn("client_id=123", url)
            self.assertTrue((Path(directory) / "strava-oauth-state.json").is_file())

    def test_callback_rejects_unknown_state(self):
        with tempfile.TemporaryDirectory() as directory:
            service = self.service(directory)
            service.authorization_url()
            with self.assertRaises(ValueError):
                service.exchange_code("code", "wrong")

    def test_expired_token_is_refreshed(self):
        with tempfile.TemporaryDirectory() as directory:
            service = self.service(directory)
            service._write(service.token_path, {"refresh_token": "refresh", "access_token": "old", "expires_at": 1})
            with patch.object(service, "_post_form", return_value={
                "refresh_token": "refresh2", "access_token": "new", "expires_at": int(time.time()) + 3600
            }):
                self.assertEqual(service.access_token(), "new")


if __name__ == "__main__":
    unittest.main()
