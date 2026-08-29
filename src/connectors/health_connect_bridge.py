"""Association et réception sécurisée du pont Android Santé Connect."""

import hashlib
import json
from pathlib import Path
import secrets
import time
from typing import Any

from .activity_ingestion import ActivityStore, activity_fingerprint
from .activity_schema import ActivitySample, NormalizedActivity


class HealthConnectBridge:
    EXERCISE_TYPES = {
        "0": "other", "2": "badminton", "4": "baseball", "5": "basketball",
        "8": "cycling", "9": "cycling_indoor", "10": "boot_camp", "11": "boxing",
        "13": "calisthenics", "14": "cricket", "16": "dance", "25": "elliptical",
        "26": "exercise_class", "27": "fencing", "28": "american_football",
        "29": "australian_football", "31": "frisbee", "32": "golf",
        "33": "guided_breathing", "34": "gymnastics", "35": "handball", "36": "hiit",
        "37": "hiking", "38": "ice_hockey", "39": "ice_skating", "44": "martial_arts",
        "46": "paddling", "47": "paragliding", "48": "pilates", "50": "racquetball",
        "51": "rock_climbing", "52": "roller_hockey", "53": "rowing",
        "54": "rowing_machine", "55": "rugby", "56": "running",
        "57": "running_treadmill", "58": "sailing", "59": "scuba_diving",
        "60": "skating", "61": "skiing", "62": "snowboarding", "63": "snowshoeing",
        "64": "soccer", "65": "softball", "66": "squash", "68": "stair_climbing",
        "69": "stair_climbing_machine", "70": "strength_training", "71": "stretching",
        "72": "surfing", "73": "swimming_open_water", "74": "swimming_pool",
        "75": "table_tennis", "76": "tennis", "78": "volleyball", "79": "walking",
        "80": "water_polo", "81": "weightlifting", "82": "wheelchair", "83": "yoga",
    }
    def __init__(self, private_dir: str | Path) -> None:
        self.private_dir = Path(private_dir)
        self.pairing_path = self.private_dir / "health-connect-pairing.json"
        self.devices_path = self.private_dir / "health-connect-devices.json"
        self.wellness_path = self.private_dir / "health-connect-wellness.json"
        self.inventory_path = self.private_dir / "health-connect-inventory.json"
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
        self._normalize_stored_activity_types()
        normalized = [self._activity(item) for item in payload.get("activities", [])]
        total = len(ActivityStore(self.activities_path).ingest(normalized)) if normalized else len(ActivityStore(self.activities_path).load())
        wellness = self._read(self.wellness_path, [])
        wellness.extend(item for item in payload.get("wellness", []) if isinstance(item, dict))
        unique = {str(item.get("source_id") or f"{item.get('type')}:{item.get('start_time')}"): item for item in wellness}
        self._write(self.wellness_path, list(unique.values()))
        inventory = {
            "received_at": int(time.time()),
            "sync_schema_version": payload.get("sync_schema_version"),
            "backfill_performed": bool(payload.get("backfill_performed", False)),
            "record_types": [item for item in payload.get("record_inventory", []) if isinstance(item, dict)],
            "skipped_record_types": [item for item in payload.get("skipped_record_types", []) if isinstance(item, dict)],
        }
        self._write(self.inventory_path, inventory)
        device["last_sync_at"] = int(time.time())
        device["last_sync_schema_version"] = payload.get("sync_schema_version")
        self._write(self.devices_path, devices)
        from src.training.post_sync_orchestrator import PostSyncOrchestrator
        assessment = PostSyncOrchestrator(self.private_dir).run("health_connect")
        return {"activities_received": len(normalized), "activities_total": total,
                "wellness_received": len(payload.get("wellness", [])), "wellness_total": len(unique),
                "record_types_available": sum(1 for item in inventory["record_types"] if int(item.get("count", 0) or 0) > 0),
                "record_types_skipped": len(inventory["skipped_record_types"]),
                "recovery_index": (assessment.get("recovery") or {}).get("atlas_recovery_index"),
                "program_proposal_available": assessment.get("program_proposal_available", False)}

    @classmethod
    def _activity(cls, item: dict[str, Any]) -> NormalizedActivity:
        samples = [
            ActivitySample(**sample)
            for sample in item.get("samples", [])
            if isinstance(sample, dict)
        ]
        raw_type = str(item.get("type", "unknown"))
        activity_type = cls.EXERCISE_TYPES.get(raw_type, raw_type)
        return NormalizedActivity(provider="health_connect",
            external_id=str(item["source_id"]), activity_type=activity_type,
            start_time=str(item["start_time"]), duration_seconds=float(item.get("duration_seconds", 0)),
            distance_meters=item.get("distance_meters"), calories_kcal=item.get("calories_kcal"),
            average_heart_rate_bpm=item.get("average_heart_rate_bpm"),
            maximum_heart_rate_bpm=item.get("maximum_heart_rate_bpm"),
            average_speed_mps=item.get("average_speed_mps"),
            elevation_gain_m=item.get("elevation_gain_m"), source_device=item.get("source_device"),
            samples=samples,
            raw_metadata={"health_connect": True, "health_connect_exercise_type": raw_type,
                          "health_connect_local_day": item.get("local_day"),
                          "lap_count": item.get("lap_count", 0),
                          "segment_count": item.get("segment_count", 0)})

    def _normalize_stored_activity_types(self) -> None:
        store = ActivityStore(self.activities_path)
        activities = store.load()
        changed = False
        for activity in activities:
            if "health_connect" not in activity.source_ids:
                continue
            normalized_type = self.EXERCISE_TYPES.get(str(activity.activity_type))
            if not normalized_type:
                continue
            activity.raw_metadata["health_connect_exercise_type"] = str(activity.activity_type)
            activity.activity_type = normalized_type
            activity.field_provenance["activity_type"] = "health_connect"
            activity.canonical_id = activity_fingerprint(activity)
            changed = True
        if changed:
            indexed = {activity.canonical_id: activity for activity in activities}
            self._write(self.activities_path, [
                activity.to_dict()
                for activity in sorted(indexed.values(), key=lambda item: item.start_time)
            ])

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
