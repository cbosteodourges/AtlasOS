"""Planification non bloquante des traitements lourds après synchronisation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from typing import Any


_LOCK = Lock()
_STATES: dict[str, dict[str, Any]] = {}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def schedule_post_sync(private_dir: str | Path, source: str) -> dict[str, Any]:
    """Démarre l'analyse en arrière-plan ou mémorise un nouveau passage."""
    key = str(Path(private_dir).resolve())
    with _LOCK:
        state = _STATES.setdefault(key, {
            "status": "idle",
            "pending": False,
            "source": source,
            "queued_at": None,
            "started_at": None,
            "finished_at": None,
            "error": None,
        })
        state["source"] = source
        state["queued_at"] = _timestamp()
        if state["status"] == "processing":
            state["pending"] = True
            return dict(state)
        state.update(status="processing", pending=False, started_at=_timestamp(), error=None)

    Thread(
        target=_run_post_sync,
        args=(key,),
        name="atlas-post-sync",
        daemon=True,
    ).start()
    return post_sync_status(private_dir)


def _run_post_sync(key: str) -> None:
    while True:
        with _LOCK:
            source = str(_STATES[key]["source"])
        try:
            from src.training.post_sync_orchestrator import PostSyncOrchestrator

            PostSyncOrchestrator(Path(key)).run(source)
            error = None
        except Exception as exc:  # Le serveur doit rester disponible si l'analyse échoue.
            error = f"{type(exc).__name__}: {exc}"

        with _LOCK:
            state = _STATES[key]
            if state["pending"]:
                state.update(pending=False, started_at=_timestamp(), error=error)
                continue
            state.update(
                status="error" if error else "complete",
                finished_at=_timestamp(),
                error=error,
            )
            return


def post_sync_status(private_dir: str | Path) -> dict[str, Any]:
    key = str(Path(private_dir).resolve())
    with _LOCK:
        return dict(_STATES.get(key, {
            "status": "idle",
            "pending": False,
            "source": None,
            "queued_at": None,
            "started_at": None,
            "finished_at": None,
            "error": None,
        }))
