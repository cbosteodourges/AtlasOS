"""Boucle Atlas déclenchée après chaque synchronisation externe."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from src.connectors.activity_ingestion import ActivityStore
from src.physiology.atlas_recovery_index import AtlasRecoveryIndex
from src.physiology.continuous_profile import ContinuousPhysiologyEstimator


PHYSIOLOGY_KEYS = {"vo2_max", "vma_kmh", "vma_training_reference_kmh",
                   "maximum_heart_rate_bpm", "sv1", "sv2"}


class PostSyncOrchestrator:
    """Recalcule les indicateurs et prépare un programme candidat explicable.

    Le programme actif n'est jamais réécrit : Atlas produit une proposition
    séparée qui doit être acceptée par l'utilisateur.
    """

    def __init__(self, private_dir: str | Path) -> None:
        self.private_dir = Path(private_dir)

    def run(self, source: str) -> dict[str, Any]:
        activities = ActivityStore(self.private_dir / "activities-unified.json").load()
        wellness = self._read("health-connect-wellness.json", [])
        recovery = AtlasRecoveryIndex().build(wellness, activities)
        self._write("atlas-recovery-index.json", recovery)

        previous = self._current_physiology()
        estimate = ContinuousPhysiologyEstimator().estimate(activities, previous)
        profile = {**previous, **({key: value for key, value in estimate.items()
                                  if key in PHYSIOLOGY_KEYS} if estimate.get("updated") else {})}
        longitudinal = self._read("physiology-longitudinal.json", {"current": previous, "history": []})
        history = list(longitudinal.get("history", []))
        history.append({"day": date.today().isoformat(), "source": source, **estimate})
        longitudinal = {"current": profile, "latest_estimate": estimate, "history": history[-365:],
                        "updated_at": datetime.now(timezone.utc).isoformat()}
        self._write("physiology-longitudinal.json", longitudinal)

        latest = recovery.get("latest") or {}
        score = latest.get("atlas_recovery_index")
        action = self._action(score)
        proposal = self._program_proposal(profile, action, score, estimate)
        assessment = {
            "source": source,
            "synchronized_at": datetime.now(timezone.utc).isoformat(),
            "recovery": latest,
            "physiology": estimate,
            "program_action": action,
            "program_proposal_available": proposal is not None,
            "requires_user_validation": True,
        }
        self._write("daily-sync-assessment.json", assessment)
        if proposal is not None:
            self._write("training-program-sync-proposal.json", proposal)
        return assessment

    @staticmethod
    def _action(score: Any) -> dict[str, Any]:
        if score is None:
            return {"level": "unknown", "decision": "keep", "reason": "Données quotidiennes insuffisantes."}
        if score >= 70:
            return {"level": "green", "decision": "keep", "reason": "Récupération compatible avec la séance prévue."}
        if score >= 45:
            return {"level": "orange", "decision": "reduce_specific_volume_25_percent",
                    "reason": "Récupération intermédiaire : réduction proposée du volume spécifique."}
        return {"level": "red", "decision": "replace_with_easy_endurance",
                "reason": "Récupération faible : endurance facile proposée à la place de l'intensité."}

    def _program_proposal(self, profile: dict[str, Any], action: dict[str, Any], score: Any,
                          estimate: dict[str, Any]) -> dict[str, Any] | None:
        program = self._read("training-program.json", None)
        if not isinstance(program, dict):
            return None
        candidate = deepcopy(program)
        candidate["athlete_snapshot"] = {**candidate.get("athlete_snapshot", {}), **profile}
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "requires_user_validation": True,
            "active_program_unchanged": True,
            "reason": action["reason"],
            "recovery_index": score,
            "daily_action": action,
            "physiology_update": estimate,
            "candidate_program": candidate,
        }

    def _current_physiology(self) -> dict[str, Any]:
        saved = self._read("physiology-longitudinal.json", {}).get("current")
        if isinstance(saved, dict) and saved:
            return saved
        program = self._read("training-program.json", {})
        snapshot = program.get("athlete_snapshot") if isinstance(program, dict) else None
        return snapshot if isinstance(snapshot, dict) else {}

    def _read(self, name: str, default: Any) -> Any:
        path = self.private_dir / name
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, name: str, value: Any) -> None:
        path = self.private_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
