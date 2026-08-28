"""OAuth Strava avec secrets hors dépôt et jetons privés renouvelables."""

import json
import os
from pathlib import Path
import secrets
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class StravaOAuthService:
    authorize_url = "https://www.strava.com/oauth/authorize"
    token_url = "https://www.strava.com/oauth/token"

    def __init__(self, private_dir: str | Path, *, client_id: str | None = None,
                 client_secret: str | None = None, redirect_uri: str | None = None) -> None:
        self.private_dir = Path(private_dir)
        self.client_id = (client_id or os.environ.get("ATLAS_STRAVA_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret or os.environ.get("ATLAS_STRAVA_CLIENT_SECRET", "")).strip()
        atlas_port = os.environ.get("ATLAS_PORT", "8010").strip() or "8010"
        default_redirect_uri = (
            f"http://localhost:{atlas_port}/api/atlas/strava/callback"
        )
        self.redirect_uri = (redirect_uri or os.environ.get(
            "ATLAS_STRAVA_REDIRECT_URI", default_redirect_uri
        )).strip()
        self.token_path = self.private_dir / "strava-oauth.json"
        self.state_path = self.private_dir / "strava-oauth-state.json"

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def status(self) -> dict[str, Any]:
        token = self._read(self.token_path)
        return {"configured": self.configured, "connected": bool(token.get("refresh_token")),
                "athlete": token.get("athlete"), "redirect_uri": self.redirect_uri}

    def authorization_url(self) -> str:
        if not self.configured:
            raise ValueError("Identifiants de l’application Strava absents.")
        state = secrets.token_urlsafe(32)
        self._write(self.state_path, {"state": state, "expires_at": int(time.time()) + 600})
        return f"{self.authorize_url}?{urlencode({'client_id': self.client_id, 'redirect_uri': self.redirect_uri, 'response_type': 'code', 'approval_prompt': 'auto', 'scope': 'read,activity:read_all', 'state': state})}"

    def exchange_code(self, code: str, state: str) -> dict[str, Any]:
        expected = self._read(self.state_path)
        if not state or not secrets.compare_digest(state, str(expected.get("state", ""))):
            raise ValueError("Réponse Strava non reconnue.")
        if int(expected.get("expires_at", 0)) < int(time.time()):
            raise ValueError("La demande Strava a expiré.")
        token = self._post_form({"client_id": self.client_id, "client_secret": self.client_secret,
                                 "code": code, "grant_type": "authorization_code"})
        self._write(self.token_path, token)
        self.state_path.unlink(missing_ok=True)
        return token

    def access_token(self) -> str:
        token = self._read(self.token_path)
        if not token.get("refresh_token"):
            raise ValueError("Compte Strava non connecté.")
        if int(token.get("expires_at", 0)) <= int(time.time()) + 60:
            refreshed = self._post_form({"client_id": self.client_id,
                "client_secret": self.client_secret, "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"]})
            token = {**token, **refreshed}
            self._write(self.token_path, token)
        return str(token["access_token"])

    def _post_form(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(self.token_url, data=urlencode(payload).encode("utf-8"),
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict) or not result.get("access_token"):
            raise ValueError("Réponse OAuth Strava invalide.")
        return result

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
