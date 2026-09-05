"""Boucle Atlas déclenchée après chaque synchronisation externe."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any

from src.connectors.activity_ingestion import ActivityStore
from src.physiology.atlas_recovery_index import (
    AtlasRecoveryIndex,
    apply_intraday_rest_adjustments,
)
from src.physiology.continuous_profile import ContinuousPhysiologyEstimator
from src.physiology.nutrition_hydration import NutritionHydrationAnalyzer
from src.training.response_followup_service import TrainingResponseFollowupService
from src.training.heart_rate_speed_profile import weekly_threshold_state_profile
from src.training.training_program_loader import TrainingProgramLoader


PHYSIOLOGY_KEYS = {"vo2_max", "vma_kmh", "vma_training_reference_kmh",
                   "maximum_heart_rate_bpm", "sv1", "sv2"}
HEALTH_CONNECT_ANALYSIS_VERSION = 10


class PostSyncOrchestrator:
    """Recalcule les indicateurs et prépare un programme candidat explicable.

    Le programme actif n'est jamais réécrit : Atlas produit une proposition
    séparée qui doit être acceptée par l'utilisateur.
    """

    def __init__(self, private_dir: str | Path) -> None:
        self.private_dir = Path(private_dir)

    def run(self, source: str) -> dict[str, Any]:
        activities = ActivityStore(self.private_dir / "activities-unified.json").load()
        wellness = self._merged_wellness()
        manual_nutrition = self._read("nutrition-hydration-manual.json", [])
        analyzed_activities = self._refresh_activity_executions(activities)
        executions = self._read("atlas-coach-executions.json", [])
        recovery = AtlasRecoveryIndex().build(
            wellness,
            activities,
            outcomes=executions,
        )
        recovery = apply_intraday_rest_adjustments(
            recovery,
            self._read("atlas-recovery-rest-periods.json", []),
        )
        self._write("atlas-recovery-index.json", recovery)

        response_followups = self._refresh_response_followups(
            executions, recovery.get("history") or []
        )

        estimate, proposed_profile, auto_applied = self.refresh_physiology(
            activities,
            source,
        )

        latest = recovery.get("latest") or {}
        weights = sorted((item for item in wellness if item.get("type") == "weight"),
                         key=lambda item: str(item.get("start_time") or ""))
        weight = weights[-1].get("value") if weights else None
        exercise_minutes = sum(item.duration_seconds for item in activities
                               if item.start_time[:10] == date.today().isoformat()) / 60
        nutrition = NutritionHydrationAnalyzer().analyze(
            [*wellness, *manual_nutrition], weight_kg=weight,
            exercise_minutes_today=exercise_minutes,
        )
        self._write("nutrition-hydration-summary.json", nutrition)
        score = latest.get("atlas_recovery_index")
        action = self._action(score)
        proposal = self._program_proposal(
            proposed_profile, action, score, estimate, nutrition,
            response_followups.get("latest_actionable"),
        )
        assessment = {
            "source": source,
            "synchronized_at": datetime.now(timezone.utc).isoformat(),
            "recovery": latest,
            "physiology": estimate,
            "nutrition_hydration": nutrition,
            "program_action": action,
            "program_proposal_available": proposal is not None,
            "health_connect_activities_analyzed": analyzed_activities,
            "requires_user_validation": True,
            "physiology_auto_applied": auto_applied,
            "training_response_followups": response_followups,
        }
        self._write("daily-sync-assessment.json", assessment)
        if proposal is not None:
            self._write("training-program-sync-proposal.json", proposal)
        return assessment

    def _refresh_response_followups(self, executions, recovery_history):
        """Ferme automatiquement la fenêtre de réponse à 24–72 heures."""
        program_path = self.private_dir / "training-program.json"
        if not program_path.is_file():
            return {"evaluated": 0, "actionable": 0, "latest_actionable": None}
        try:
            workouts = TrainingProgramLoader().load(program_path)
            contexts = self._read("atlas-coach-workout-contexts.json", [])
            followups = TrainingResponseFollowupService().build(
                workouts, executions, recovery_history, contexts
            )
        except (TypeError, ValueError, KeyError):
            return {"evaluated": 0, "actionable": 0, "latest_actionable": None}
        self._write("training-response-followups.json", followups)
        actionable_items = [
            item for item in followups
            if item.get("next_decision_context", {}).get("usable")
        ]
        latest = actionable_items[-1] if actionable_items else None
        return {
            "evaluated": len(followups),
            "actionable": len(actionable_items),
            "latest_actionable": (
                {
                    "workout_id": latest.get("workout_id"),
                    "session_started_at": latest.get("session_started_at"),
                    **latest.get("next_decision_context", {}),
                }
                if latest else None
            ),
        }

    def refresh_physiology(
        self,
        activities: list[Any] | None = None,
        source: str = "manual_physiology_refresh",
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        """Recalcule uniquement le profil, sans relancer toute la synchronisation."""

        activities = activities if activities is not None else ActivityStore(
            self.private_dir / "activities-unified.json"
        ).load()
        previous = self._current_physiology()
        estimate = ContinuousPhysiologyEstimator().estimate(activities, previous)
        proposed_profile = {
            **previous,
            **(
                {key: value for key, value in estimate.items() if key in PHYSIOLOGY_KEYS}
                if estimate.get("updated") else {}
            ),
        }
        longitudinal = self._read(
            "physiology-longitudinal.json",
            {"current": previous, "history": []},
        )
        threshold_evolution = weekly_threshold_state_profile(
            self._read("atlas-coach-executions.json", []),
            previous,
        )
        profile, session_applied = self._auto_apply_physiology(previous, estimate)
        profile, weekly_applied = self._apply_weekly_threshold_evolution(
            profile,
            threshold_evolution,
            longitudinal.get("threshold_evolution_history") or [],
        )
        auto_applied = [*session_applied, *weekly_applied]
        proposed_profile = {**proposed_profile, **profile}
        history = [
            item for item in longitudinal.get("history", [])
            if item.get("schema") == "validated_profile_v1"
        ]
        history.extend(self._retrospective_physiology(activities, profile))
        now = datetime.now(timezone.utc)
        assessment = estimate.get("session_assessment") or {}
        occurred_at = (
            assessment.get("start_time")
            or estimate.get("updated_at")
            or now.isoformat()
        )
        today = str(occurred_at)[:10] or date.today().isoformat()
        sv1 = profile.get("sv1") or {}
        sv2 = profile.get("sv2") or {}
        snapshot = {
            "day": today,
            "timestamp": occurred_at,
            "activity_id": assessment.get("activity_id"),
            "source": source,
            "schema": "validated_profile_v1",
            "vo2_max": profile.get("vo2_max"),
            "vma_kmh": (
                profile.get("vma_estimated_from_vo2_kmh")
                or profile.get("vma_kmh")
                or profile.get("vma_training_reference_kmh")
            ),
            "sv1_speed_kmh": sv1.get("speed_kmh"),
            "sv1_heart_rate_bpm": sv1.get("heart_rate_bpm"),
            "sv2_speed_kmh": sv2.get("speed_kmh"),
            "sv2_heart_rate_bpm": sv2.get("heart_rate_bpm"),
            "maximum_heart_rate_bpm": profile.get("maximum_heart_rate_bpm"),
            "estimator_updated": bool(estimate.get("updated")),
            "estimator_confidence": estimate.get("confidence"),
            "auto_applied": auto_applied,
        }
        # La courbe mémorise chaque décision physiologique effective, y
        # compris plusieurs ajustements le même jour. Un recalcul sans
        # modification ne crée aucun faux point.
        if auto_applied or not history:
            snapshot_key = (
                snapshot.get("activity_id"),
                tuple(snapshot.get("auto_applied") or []),
                snapshot.get("vo2_max"),
                snapshot.get("vma_kmh"),
                snapshot.get("sv1_speed_kmh"),
                snapshot.get("sv1_heart_rate_bpm"),
                snapshot.get("sv2_speed_kmh"),
                snapshot.get("sv2_heart_rate_bpm"),
            )
            existing_keys = {
                (
                    item.get("activity_id"),
                    tuple(item.get("auto_applied") or []),
                    item.get("vo2_max"),
                    item.get("vma_kmh"),
                    item.get("sv1_speed_kmh"),
                    item.get("sv1_heart_rate_bpm"),
                    item.get("sv2_speed_kmh"),
                    item.get("sv2_heart_rate_bpm"),
                )
                for item in history
                if item.get("schema") == "validated_profile_v1"
            }
            if snapshot_key not in existing_keys:
                history.append(snapshot)
        history.sort(
            key=lambda item: str(item.get("timestamp") or item.get("day") or "")
        )
        threshold_history = [
            item for item in longitudinal.get("threshold_evolution_history", [])
            if item.get("week") != threshold_evolution.get("week")
        ]
        threshold_history.append({
            **threshold_evolution,
            "applied": weekly_applied,
        })
        if weekly_applied:
            self._propagate_validated_physiology_to_program(
                previous, profile, weekly_applied
            )
        self._write("physiology-longitudinal.json", {
            "current": profile,
            "latest_estimate": estimate,
            "latest_threshold_evolution": threshold_evolution,
            "threshold_evolution_history": threshold_history[-104:],
            "history": history[-5000:],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return estimate, proposed_profile, auto_applied

    @staticmethod
    def _apply_weekly_threshold_evolution(
        profile: dict[str, Any],
        evolution: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], list[str]]:
        """Valide uniquement deux semaines consécutives concordantes."""

        result = deepcopy(profile)
        applied: list[str] = []
        current_week = evolution.get("week")
        previous_weeks = [
            item for item in history
            if item.get("week") and item.get("week") != current_week
        ]
        previous_evolution = previous_weeks[-1] if previous_weeks else {}
        previous_states = previous_evolution.get("states") or {}
        for threshold in ("sv1", "sv2"):
            state = (evolution.get("states") or {}).get(threshold) or {}
            prior = previous_states.get(threshold) or {}
            if (
                not state.get("usable")
                or not prior.get("usable")
                or state.get("direction") not in {"progression", "regression"}
                or state.get("direction") != prior.get("direction")
                or int(state.get("confidence") or 0) < 65
                or int(prior.get("confidence") or 0) < 65
            ):
                continue
            current = result.get(threshold) or {}
            projection = state.get("projection") or {}

            def bounded(old, new, limit, digits):
                try:
                    old_value, new_value = float(old), float(new)
                except (TypeError, ValueError):
                    return new
                return round(max(old_value - limit, min(old_value + limit, new_value)), digits)

            updated = {
                **current,
                "speed_kmh": bounded(
                    current.get("speed_kmh"), projection.get("speed_kmh"), .15, 2
                ),
                "heart_rate_bpm": bounded(
                    current.get("heart_rate_bpm"),
                    projection.get("heart_rate_bpm"),
                    2,
                    0,
                ),
                "status": "weekly_validated_threshold_v2",
                "updated_at": evolution.get("as_of"),
                "validation_week": current_week,
                "confidence": state.get("confidence"),
                "direction": state.get("direction"),
                "evidence": (
                    "Deux semaines concordantes : relation allure–FC et "
                    "blocs spécifiques proches du seuil."
                ),
            }
            if updated != current:
                result[threshold] = updated
                applied.append(threshold)
        return result, applied

    def _propagate_validated_physiology_to_program(
        self,
        previous: dict[str, Any],
        profile: dict[str, Any],
        applied: list[str],
    ) -> None:
        """Répercute les seuils validés dans le profil du programme actif.

        Les séances existantes restent identifiables et ne sont jamais
        dupliquées. Les générateurs et analyses suivants relisent ensuite ce
        même instantané validé.
        """

        program = self._read("training-program.json", None)
        if not isinstance(program, dict):
            return
        snapshot = program.get("athlete_snapshot") or {}
        for key in applied:
            if key in {"sv1", "sv2"}:
                snapshot[key] = deepcopy(profile.get(key) or {})
            elif key in {"vma_kmh", "vo2_max"}:
                snapshot[key] = profile.get(key)
        program["athlete_snapshot"] = snapshot
        retargeted = self._retarget_future_workouts(
            program, previous, profile, applied
        )
        program["automatic_physiology_revision"] = {
            "schema": "threshold_state_v2",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": applied,
            "source": "weekly_hr_speed_threshold_model",
            "future_workouts_retargeted": retargeted,
            "previous": {
                key: previous.get(key) for key in applied
            },
        }
        self._write("training-program.json", program)

    @staticmethod
    def _retarget_future_workouts(
        program: dict[str, Any],
        previous: dict[str, Any],
        profile: dict[str, Any],
        applied: list[str],
    ) -> int:
        """Ajuste les cibles des séances futures sans changer leur identité."""

        def threshold_values(source, key):
            value = source.get(key) or {}
            return value if isinstance(value, dict) else {}

        ratios: dict[str, float] = {}
        heart_rate_deltas: dict[str, float] = {}
        for key in ("sv1", "sv2"):
            if key not in applied:
                continue
            old = threshold_values(previous, key)
            new = threshold_values(profile, key)
            try:
                ratio = float(new.get("speed_kmh")) / float(old.get("speed_kmh"))
                ratios[key] = max(.98, min(1.02, ratio))
            except (TypeError, ValueError, ZeroDivisionError):
                pass
            try:
                heart_rate_deltas[key] = max(
                    -2, min(2, float(new.get("heart_rate_bpm")) - float(old.get("heart_rate_bpm")))
                )
            except (TypeError, ValueError):
                pass

        if "vma_kmh" in applied:
            try:
                ratios["vma"] = max(
                    .98,
                    min(1.02, float(profile["vma_kmh"]) / float(previous["vma_kmh"])),
                )
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                pass

        def family(workout, block):
            block_description = " ".join(str(value or "").lower() for value in (
                block.get("block_type"), block.get("type"), block.get("name"),
            ))
            workout_description = " ".join(str(value or "").lower() for value in (
                workout.get("workout_type"), workout.get("title"),
            ))
            if any(token in block_description for token in ("sv2", "threshold", "seuil", "subthreshold", "sous seuil")):
                return "sv2"
            if any(token in block_description for token in ("vma", "vo2", "vo₂")):
                return "vma"
            if any(token in block_description for token in ("warmup", "échauff", "cooldown", "retour au calme", "endurance", "easy", "z1", "z2", "recovery", "récup")):
                return "sv1"
            if any(token in workout_description for token in ("sv2", "threshold", "seuil", "subthreshold", "sous seuil")):
                return "sv2"
            if any(token in workout_description for token in ("vma", "vo2", "vo₂")):
                return "vma"
            if any(token in workout_description for token in ("endurance", "easy", "z1", "z2", "long")):
                return "sv1"
            return None

        changed_workouts = 0
        today = date.today().isoformat()
        for week in program.get("weeks") or []:
            for workout in week.get("workouts") or []:
                workout_day = str(workout.get("workout_date") or "")[:10]
                if workout_day and workout_day < today:
                    continue
                if workout.get("historical_execution") or workout.get("history_status") == "completed":
                    continue
                workout_changed = False
                for block in workout.get("blocks") or []:
                    target = block.get("target") or {}
                    key = family(workout, block)
                    factor = ratios.get(key)
                    if factor is not None:
                        for field in ("speed_min_kmh", "speed_max_kmh"):
                            try:
                                original = float(target[field])
                            except (KeyError, TypeError, ValueError):
                                continue
                            adjusted = round(original * factor, 1)
                            if adjusted != target[field]:
                                target[field] = adjusted
                                workout_changed = True
                    delta_hr = heart_rate_deltas.get(key)
                    if delta_hr is not None:
                        for field in ("heart_rate_min_bpm", "heart_rate_max_bpm"):
                            try:
                                original = float(target[field])
                            except (KeyError, TypeError, ValueError):
                                continue
                            adjusted = round(original + delta_hr)
                            if adjusted != target[field]:
                                target[field] = adjusted
                                workout_changed = True
                    if target:
                        block["target"] = target
                if workout_changed:
                    workout["physiology_revision"] = {
                        "schema": "threshold_state_v2",
                        "reason": "Seuil hebdomadaire validé sur deux semaines concordantes.",
                        "metrics": applied,
                    }
                    changed_workouts += 1
        return changed_workouts

    def _refresh_activity_executions(self, activities: list[Any]) -> int:
        """Analyse les activités Health Connect sans exiger de fichier FIT."""

        program_path = self.private_dir / "training-program.json"
        if not program_path.is_file():
            return 0

        # Le moteur utilisé par l'import FIT accepte déjà toute activité
        # normalisée. Health Connect passe donc exactement par les mêmes
        # analyses et le même rapprochement avec le programme.
        from scripts.sync_atlas_coach_pilot import (
            build_record,
            confirm_matched_workouts,
            load_analysis_profile,
            load_optional_workouts,
        )
        from src.training import TrainingProgramLoader

        loader = TrainingProgramLoader()
        workouts = loader.load(program_path)
        optional_path = (
            self.private_dir / "atlas-coach-optional-workouts.json"
        )
        if optional_path.is_file():
            workouts.extend(
                load_optional_workouts(optional_path, loader)
            )
        profile = load_analysis_profile(program_path)
        history = self._read("atlas-coach-executions.json", [])
        history = history if isinstance(history, list) else []
        by_activity = {
            str(item.get("activity_id") or ""): item
            for item in history
            if isinstance(item, dict)
        }
        by_source = {
            (str(provider), str(external_id)): item
            for item in history
            if isinstance(item, dict)
            for provider, external_id in {
                **dict(item.get("source_ids") or {}),
                str(item.get("provider") or ""): str(item.get("external_id") or ""),
            }.items()
            if provider and external_id
        }
        refreshed = []
        refreshed_source_keys = set()

        for activity in activities:
            source_ids = getattr(activity, "source_ids", {}) or {}
            provider = str(getattr(activity, "provider", "") or "")
            if (
                "health_connect" not in source_ids
                and provider != "health_connect"
            ):
                continue
            activity_id = str(getattr(activity, "atlas_id", "") or "")
            source_keys = {
                (str(provider_name), str(external_id))
                for provider_name, external_id in {
                    **source_ids,
                    provider: getattr(activity, "external_id", ""),
                }.items()
                if provider_name and external_id
            }
            previous = by_activity.get(activity_id) or next(
                (by_source[key] for key in source_keys if key in by_source),
                None,
            )
            if (
                isinstance(previous, dict)
                and previous.get("atlas_workout_match") is not None
                and previous.get("health_connect_analysis_version")
                == HEALTH_CONNECT_ANALYSIS_VERSION
            ):
                continue
            try:
                record = build_record(
                    activity,
                    workouts,
                    loader,
                    profile,
                )
                record["health_connect_analysis_version"] = (
                    HEALTH_CONNECT_ANALYSIS_VERSION
                )
            except (TypeError, ValueError, KeyError):
                # Une activité ancienne incomplète ne doit jamais bloquer la
                # synchronisation des données récentes et du wellness.
                continue
            by_activity[activity_id] = record
            refreshed.append(record)
            refreshed_source_keys.update(source_keys)

        if not refreshed:
            return 0

        updated = [
            item
            for item in history
            if str(item.get("activity_id") or "") not in {
                str(record.get("activity_id") or "") for record in refreshed
            }
            and (
                str(item.get("provider") or ""),
                str(item.get("external_id") or ""),
            ) not in refreshed_source_keys
        ]
        updated.extend(refreshed)
        updated.sort(key=lambda item: str(item.get("start_time") or ""))
        self._write("atlas-coach-executions.json", updated)
        confirm_matched_workouts(
            refreshed,
            self.private_dir / "atlas-coach-workout-decisions.json",
        )
        return len(refreshed)

    @staticmethod
    def _retrospective_physiology(activities: list[Any], profile: dict[str, Any]) -> list[dict[str, Any]]:
        """Reconstruit une tendance terrain hebdomadaire, puis l'ancre sur le profil validé."""

        runs = sorted(
            (
                item for item in activities
                if str(getattr(item, "activity_type", "")).lower()
                in {"run", "running", "trail_running", "56"}
            ),
            key=lambda item: str(getattr(item, "start_time", "")),
        )
        if not runs:
            return []

        def activity_day(item: Any) -> date | None:
            try:
                return datetime.fromisoformat(
                    str(getattr(item, "start_time", "")).replace("Z", "+00:00")
                ).date()
            except (TypeError, ValueError):
                return None

        dated = [(activity_day(item), item) for item in runs]
        dated = [(day, item) for day, item in dated if day is not None]
        if not dated:
            return []

        first_day, last_day = dated[0][0], dated[-1][0]
        cursor = min(last_day, first_day + timedelta(days=41))
        endpoints = []
        while cursor < last_day:
            endpoints.append(cursor)
            cursor += timedelta(days=7)
        endpoints.append(last_day)

        maximum_hr = profile.get("maximum_heart_rate_bpm")
        result = []
        for endpoint in endpoints:
            start = endpoint - timedelta(days=41)
            window = [item for day, item in dated if start <= day <= endpoint]
            estimate = ContinuousPhysiologyEstimator().estimate(
                window,
                {"maximum_heart_rate_bpm": maximum_hr},
            )
            if not estimate.get("updated"):
                continue
            sv1 = estimate.get("sv1") or {}
            sv2 = estimate.get("sv2") or {}
            observed_maximum_hr = max(
                (
                    float(getattr(item, "maximum_heart_rate_bpm"))
                    for item in window
                    if getattr(item, "maximum_heart_rate_bpm", None) is not None
                    and 100 <= float(getattr(item, "maximum_heart_rate_bpm")) <= 230
                ),
                default=maximum_hr,
            )
            result.append({
                "day": endpoint.isoformat(),
                "source": "historical_fit",
                "schema": "atlas_retrospective_v1",
                "method": "tendance terrain hebdomadaire sur 42 jours, recalée sur la référence actuelle",
                "vo2_max": estimate.get("vo2_max"),
                "vma_kmh": estimate.get("vma_kmh"),
                "sv1_speed_kmh": sv1.get("speed_kmh"),
                "sv2_speed_kmh": sv2.get("speed_kmh"),
                "maximum_heart_rate_bpm": maximum_hr,
                "observed_maximum_heart_rate_bpm": observed_maximum_hr,
                "estimator_confidence": estimate.get("confidence"),
                "evidence_sessions": estimate.get("evidence_sessions"),
            })

        sv1_profile = profile.get("sv1") or {}
        sv2_profile = profile.get("sv2") or {}
        targets = {
            "vo2_max": profile.get("vo2_max"),
            "vma_kmh": (
                profile.get("vma_estimated_from_vo2_kmh")
                or profile.get("vma_kmh")
                or profile.get("vma_training_reference_kmh")
            ),
            "sv1_speed_kmh": sv1_profile.get("speed_kmh"),
            "sv2_speed_kmh": sv2_profile.get("speed_kmh"),
            "maximum_heart_rate_bpm": maximum_hr,
        }
        bounds = {
            "vo2_max": (20, 90, 1),
            "vma_kmh": (6, 30, 2),
            "sv1_speed_kmh": (5, 24, 2),
            "sv2_speed_kmh": (6, 28, 2),
            "maximum_heart_rate_bpm": (100, 230, 0),
        }
        for field, target in targets.items():
            values = [item.get(field) for item in result if item.get(field) is not None]
            if target is None or not values:
                continue
            offset = float(target) - float(values[-1])
            minimum, maximum, digits = bounds[field]
            for item in result:
                if item.get(field) is not None:
                    item[field] = round(
                        max(minimum, min(maximum, float(item[field]) + offset)),
                        digits,
                    )
        return result

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
                          estimate: dict[str, Any], nutrition: dict[str, Any],
                          training_response: dict[str, Any] | None = None) -> dict[str, Any] | None:
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
            "nutrition_hydration_context": nutrition,
            "training_response_context_24_72h": training_response,
            "candidate_program": candidate,
        }

    def _merged_wellness(self) -> list[dict[str, Any]]:
        """Complète Santé Connect avec les journées Garmin absentes."""
        wellness = self._read("health-connect-wellness.json", [])
        merged = [
            dict(item) for item in wellness
            if isinstance(item, dict)
        ]
        sleep_days = {
            stamp.date().isoformat()
            for item in merged if item.get("type") == "sleep"
            for stamp in [self._timestamp(item.get("end_time"))]
            if stamp is not None
        }
        metric_keys = {
            (
                str(item.get("type") or ""),
                stamp.date().isoformat(),
            )
            for item in merged
            for stamp in [self._timestamp(item.get("start_time"))]
            if stamp is not None
        }
        cache = self._read("garmin-wellness-snapshot-cache.json", {})
        for archive in (cache.get("archives") or {}).values():
            snapshot = (
                archive.get("snapshot")
                if isinstance(archive, dict) else None
            )
            if not isinstance(snapshot, dict):
                continue
            day = str(snapshot.get("day") or "")[:10]
            if not day:
                continue
            end = datetime.fromisoformat(
                f"{day}T06:00:00+00:00"
            )
            duration_minutes = snapshot.get("sleep_duration_minutes")
            if day not in sleep_days and duration_minutes:
                start = end - timedelta(minutes=float(duration_minutes))
                merged.append({
                    "type": "sleep",
                    "source_id": f"garmin-wellness-sleep-{day}",
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "stages": [],
                    "source": "garmin_wellness",
                })
                sleep_days.add(day)
            for kind, field in (
                ("resting_heart_rate", "resting_heart_rate_bpm"),
                ("hrv_rmssd", "hrv_last_night_ms"),
            ):
                value = snapshot.get(field)
                if value is None or (kind, day) in metric_keys:
                    continue
                merged.append({
                    "type": kind,
                    "source_id": f"garmin-wellness-{kind}-{day}",
                    "start_time": end.isoformat(),
                    "value": value,
                    "source": "garmin_wellness",
                })
                metric_keys.add((kind, day))
        return merged

    @staticmethod
    def _timestamp(value: Any) -> datetime | None:
        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            return None

    def _current_physiology(self) -> dict[str, Any]:
        saved = self._read("physiology-longitudinal.json", {}).get("current")
        saved = saved if isinstance(saved, dict) else {}
        if saved.get("vo2_max_status") == "auto_validated_quality_session":
            try:
                saved = {**saved, "vo2_max": round(float(saved["vo2_max"]))}
            except (KeyError, TypeError, ValueError):
                pass
        program = self._read("training-program.json", {})
        snapshot = program.get("athlete_snapshot") if isinstance(program, dict) else None
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        athlete = self._read("athlete-profile.json", {})
        athlete_physiology = (
            athlete.get("physiological")
            if isinstance(athlete, dict) else None
        )
        athlete_physiology = (
            athlete_physiology
            if isinstance(athlete_physiology, dict) else {}
        )
        # Le programme fournit le socle initial ; la mémoire longitudinale porte
        # ensuite les validations et les mises à jour physiologiques plus récentes.
        profile = {**snapshot, **saved}
        threshold_hr = (
            athlete_physiology.get("threshold_heart_rate_bpm")
            or snapshot.get("threshold_heart_rate_bpm")
        )
        sv2 = profile.get("sv2") or {}
        weak_sv2_statuses = {
            None,
            "",
            "estimated",
            "longitudinal",
            "longitudinal_estimate",
        }
        if threshold_hr is not None and (
            sv2.get("heart_rate_bpm") is None
            or sv2.get("status") in weak_sv2_statuses
        ):
            profile["sv2"] = {
                **sv2,
                "heart_rate_bpm": threshold_hr,
                "status": "validated_threshold_reference",
            }
        return profile

    @staticmethod
    def _auto_apply_physiology(
        previous: dict[str, Any],
        estimate: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Applique l'avis de chaque séance avec des variations bornées."""

        profile = deepcopy(previous)
        applied: list[str] = []
        observed = estimate.get("observed") or {}
        candidate = estimate.get("vo2_max")
        previous_vo2 = previous.get("vo2_max")
        try:
            candidate = float(candidate)
            previous_vo2 = float(previous_vo2)
        except (TypeError, ValueError):
            candidate = previous_vo2 = None
        if (
            candidate is not None
            and previous_vo2 is not None
            and estimate.get("decision") == "increase_candidate"
            and observed.get("fast_vo2_signal") is True
            and 0 < candidate - previous_vo2 <= 1.0
        ):
            profile["vo2_max"] = candidate
            profile["vo2_max_status"] = "auto_validated_quality_session"
            profile["vo2_max_updated_at"] = estimate.get("updated_at")
            applied.append("vo2_max")

        assessment = estimate.get("session_assessment") or {}
        activity_id = assessment.get("activity_id")
        if (
            not activity_id
            or activity_id == previous.get("last_session_assessment_id")
        ):
            return profile, applied
        signals = assessment.get("signals") or {}

        def adjusted_value(
            old: Any,
            new: Any,
            limit: float,
            digits: int = 2,
        ):
            try:
                old_number = float(old)
                new_number = float(new)
            except (TypeError, ValueError):
                return new
            return round(
                max(
                    old_number - limit,
                    min(old_number + limit, new_number),
                ),
                digits,
            )

        vma_signal = signals.get("vma_kmh") or {}
        if float(vma_signal.get("confidence") or 0) >= .80:
            profile["vma_kmh"] = adjusted_value(
                profile.get("vma_kmh")
                or profile.get("vma_training_reference_kmh"),
                vma_signal.get("candidate"),
                .20,
            )
            profile["vma_training_reference_kmh"] = profile["vma_kmh"]
            applied.append("vma_kmh")

        # SV1 et SV2 ne sont plus déplacés par une séance isolée. Les signaux
        # restent mémorisés comme preuves, puis le moteur hebdomadaire exige
        # deux semaines concordantes avant toute validation automatique.
        pending_thresholds = {
            threshold: signals[threshold]
            for threshold in ("sv1", "sv2")
            if threshold in signals
        }
        if pending_thresholds:
            profile["pending_threshold_observations"] = {
                "activity_id": activity_id,
                "updated_at": estimate.get("updated_at"),
                "signals": pending_thresholds,
            }

        if signals:
            profile["last_session_assessment_id"] = activity_id
            profile["last_session_assessment"] = assessment
        return profile, applied

    def _read(self, name: str, default: Any) -> Any:
        path = self.private_dir / name
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, name: str, value: Any) -> None:
        path = self.private_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=self._json_default,
            ) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        raise TypeError(
            f"Type non sérialisable : {type(value).__name__}"
        )
