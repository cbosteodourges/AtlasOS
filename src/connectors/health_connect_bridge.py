"""Association et réception sécurisée du pont Android Santé Connect."""

import hashlib
import json
from pathlib import Path
import secrets
import time
from typing import Any

from .activity_ingestion import ActivityStore
from .activity_schema import NormalizedActivity


class HealthConnectBridge:
    def __init__(self, private_dir: str | Path) -> None:
        self.private_dir = Path(private_dir)
        self.pairing_path = self.private_dir / "health-connect-pairing.json"
        self.devices_path = self.private_dir / "health-connect-devices.json"
        self.wellness_path = self.private_dir / "health-connect-wellness.json"
        self.activities_path = self.private_dir / "activities-unified.json"

    def create_pairing_code(self) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._write(self.pairing_path, {"code_hash": self._hash(code),
            "expires_at": int(time.time()) + 600})
        return code

    def pair(self, code: str, device: dict[str, Any]) -> str:
        pairing = self._read(self.pairing_path, {})
        if int(pairing.get("expires_at", 0)) < int(time.time()):
            raise ValueError("Le code d’association a expiré.")
        if not secrets.compare_digest(str(pairing.get("code_hash", "")), self._hash(code)):
            raise ValueError("Code d’association incorrect.")
        token = secrets.token_urlsafe(48)
        devices = self._read(self.devices_path, [])
        devices.append({"token_hash": self._hash(token), "device": device,
                        "paired_at": int(time.time()), "last_sync_at": None})
        self._write(self.devices_path, devices[-10:])
        self.pairing_path.unlink(missing_ok=True)
        return token

    def ingest(self, token: str, payload: dict[str, Any]) -> dict[str, int]:
        devices = self._read(self.devices_path, [])
        token_hash = self._hash(token)
        device = next((item for item in devices if secrets.compare_digest(
            str(item.get("token_hash", "")), token_hash)), None)
        if device is None:
            raise PermissionError("Téléphone Santé Connect non associé.")
        normalized = [self._activity(item) for item in payload.get("activities", [])]
        total = len(ActivityStore(self.activities_path).ingest(normalized)) if normalized else len(ActivityStore(self.activities_path).load())
        wellness = self._read(self.wellness_path, [])
        wellness.extend(item for item in payload.get("wellness", []) if isinstance(item, dict))
        unique = {str(item.get("source_id") or f"{item.get('type')}:{item.get('start_time')}"): item for item in wellness}
        self._write(self.wellness_path, list(unique.values()))
        device["last_sync_at"] = int(time.time())
        self._write(self.devices_path, devices)
        return {"activities_received": len(normalized), "activities_total": total,
                "wellness_received": len(payload.get("wellness", [])), "wellness_total": len(unique)}

    @staticmethod
    def _activity(item: dict[str, Any]) -> NormalizedActivity:
        return NormalizedActivity(provider="health_connect",
            external_id=str(item["source_id"]), activity_type=str(item.get("type", "unknown")),
            start_time=str(item["start_time"]), duration_seconds=float(item.get("duration_seconds", 0)),
            distance_meters=item.get("distance_meters"), calories_kcal=item.get("calories_kcal"),
            average_heart_rate_bpm=item.get("average_heart_rate_bpm"),
            maximum_heart_rate_bpm=item.get("maximum_heart_rate_bpm"),
            elevation_gain_m=item.get("elevation_gain_m"), source_device=item.get("source_device"),
            raw_metadata={"health_connect": True})

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
