"""
ATLAS OS
Fusion de l'historique d'entraînement et de la récupération.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any, Iterable, Optional

from src.connectors.garmin_wellness import (
    DailyRecoverySnapshot,
)
from src.physiology import (
    GarminRecoveryAdapter,
    PhysiologyEngine,
)


@dataclass(slots=True)
class FusedActivityResponse:
    """Séance enrichie avec sa réponse physiologique."""

    activity_id: str
    activity_date: date
    original_sport: str
    canonical_sport: str
    session_type: str

    duration_minutes: float
    distance_km: float
    elevation_gain_m: float

    physiological_load_score: float
    biomechanical_load_score: float
    intensity_score: float
    session_load_units: float

    readiness_before: Optional[float] = None
    readiness_24h: Optional[float] = None
    readiness_48h: Optional[float] = None
    readiness_72h: Optional[float] = None

    response_24h: Optional[float] = None
    response_48h: Optional[float] = None
    response_72h: Optional[float] = None
    recovered_within_hours: Optional[int] = None

    user_declared_type: Optional[str] = None
    user_context: str = ""
    confidence_score: int = 0
    automatic_learning_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["activity_date"] = self.activity_date.isoformat()
        return result


@dataclass(slots=True)
class SportResponseSummary:
    """Tolérance individuelle observée pour un sport."""

    sport: str
    activity_count: int
    total_duration_hours: float
    total_distance_km: float
    average_session_load: float
    average_response_24h: Optional[float]
    average_response_48h: Optional[float]
    average_recovery_hours: Optional[float]
    confidence_score: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TrainingHistoryFusionResult:
    """Mémoire fusionnée utilisable par Atlas Coach."""

    analysis_date: date
    activity_count: int
    wellness_day_count: int
    wellness_coverage_percent: float

    acute_load_7d: float
    chronic_load_28d_weekly: float
    acute_chronic_load_ratio: Optional[float]

    activities: list[FusedActivityResponse] = field(
        default_factory=list
    )
    sports: list[SportResponseSummary] = field(
        default_factory=list
    )
    explanations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "activity_count": self.activity_count,
            "wellness_day_count": self.wellness_day_count,
            "wellness_coverage_percent": (
                self.wellness_coverage_percent
            ),
            "acute_load_7d": self.acute_load_7d,
            "chronic_load_28d_weekly": (
                self.chronic_load_28d_weekly
            ),
            "acute_chronic_load_ratio": (
                self.acute_chronic_load_ratio
            ),
            "activities": [
                item.to_dict()
                for item in self.activities
            ],
            "sports": [
                item.to_dict()
                for item in self.sports
            ],
            "explanations": self.explanations,
            "warnings": self.warnings,
        }


class TrainingHistoryFusionAnalyzer:
    """
    Relie les séances FIT aux réponses Wellness à 24–72 h.

    Les charges produites sont des unités Atlas
    individualisées. Le ratio aigu/chronique reste un
    indicateur descriptif et non un prédicteur de blessure.
    """

    SPORT_ALIASES = {
        "road": "cycling",
        "cycling": "cycling",
        "mountain_biking": "cycling",
        "gravel_cycling": "cycling",
        "running": "running",
        "trail": "running",
        "ultra": "running",
        "treadmill": "running",
        "walking": "walking",
        "hiking": "hiking",
        "hiit": "strength",
    }

    def analyze(
        self,
        executions: Iterable[dict[str, Any]],
        wellness: Iterable[DailyRecoverySnapshot],
        *,
        contexts: Optional[dict[str, dict[str, Any]]] = None,
        analysis_date: Optional[date] = None,
    ) -> TrainingHistoryFusionResult:
        """Construit la mémoire individuelle complète."""

        records = list(executions)
        snapshots = sorted(
            wellness,
            key=lambda item: item.day,
        )
        context_map = contexts or {}

        if analysis_date is None:
            analysis_date = (
                snapshots[-1].day
                if snapshots
                else date.today()
            )

        readiness = self._readiness_by_day(snapshots)
        snapshot_days = {item.day for item in snapshots}

        fused = [
            self._fuse_activity(
                record,
                readiness,
                context_map,
            )
            for record in records
        ]
        fused.sort(key=lambda item: item.activity_date)

        recent_28 = [
            item
            for item in fused
            if (
                analysis_date - timedelta(days=27)
                <= item.activity_date
                <= analysis_date
            )
        ]
        recent_7 = [
            item
            for item in recent_28
            if (
                analysis_date - timedelta(days=6)
                <= item.activity_date
            )
        ]

        acute_load = round(
            sum(item.session_load_units for item in recent_7),
            1,
        )
        chronic_weekly = round(
            sum(
                item.session_load_units
                for item in recent_28
            )
            / 4,
            1,
        )
        load_ratio = (
            round(acute_load / chronic_weekly, 2)
            if chronic_weekly > 0
            else None
        )

        activity_days = {
            item.activity_date
            for item in fused
        }
        covered_days = len(activity_days & snapshot_days)
        coverage = (
            round(covered_days / len(activity_days) * 100, 1)
            if activity_days
            else 0.0
        )

        sports = self._sport_summaries(fused)
        explanations = self._explanations(
            fused,
            sports,
            acute_load,
            chronic_weekly,
            load_ratio,
        )
        warnings = self._warnings(
            fused,
            coverage,
            load_ratio,
        )

        return TrainingHistoryFusionResult(
            analysis_date=analysis_date,
            activity_count=len(fused),
            wellness_day_count=len(snapshots),
            wellness_coverage_percent=coverage,
            acute_load_7d=acute_load,
            chronic_load_28d_weekly=chronic_weekly,
            acute_chronic_load_ratio=load_ratio,
            activities=fused,
            sports=sports,
            explanations=explanations,
            warnings=warnings,
        )

    def _fuse_activity(
        self,
        record: dict[str, Any],
        readiness: dict[date, float],
        contexts: dict[str, dict[str, Any]],
    ) -> FusedActivityResponse:
        fingerprint = record.get("fingerprint") or {}
        detailed = record.get("detailed_analysis") or {}

        activity_id = str(
            record.get("activity_id")
            or fingerprint.get("activity_id")
            or ""
        )
        activity_date = datetime.fromisoformat(
            str(record["start_time"])
        ).date()

        context = contexts.get(activity_id, {})
        original_sport = str(
            fingerprint.get("sport", "unknown")
        ).strip().lower()

        declared_type = self._optional_text(
            context.get("activity_type")
        )
        canonical_sport = (
            declared_type
            or self.SPORT_ALIASES.get(
                original_sport,
                original_sport,
            )
        )

        duration = self._number(
            fingerprint.get("duration_minutes")
        )
        distance = self._number(
            fingerprint.get("distance_km")
        )
        elevation = self._number(
            fingerprint.get("elevation_gain_m")
        )

        physiological = self._number(
            detailed.get("physiological_load_score"),
            fallback=fingerprint.get(
                "internal_load_score"
            ),
        )
        biomechanical = self._number(
            detailed.get("biomechanical_load_score"),
            fallback=fingerprint.get(
                "external_load_score"
            ),
        )
        intensity = self._number(
            fingerprint.get("intensity_score")
        )

        composite_load = (
            physiological * 0.45
            + biomechanical * 0.35
            + intensity * 0.20
        )
        session_load = round(
            composite_load * max(duration, 1.0) / 60,
            1,
        )

        before = readiness.get(activity_date)
        after_24 = readiness.get(
            activity_date + timedelta(days=1)
        )
        after_48 = readiness.get(
            activity_date + timedelta(days=2)
        )
        after_72 = readiness.get(
            activity_date + timedelta(days=3)
        )

        recovered = self._recovery_hours(
            before,
            after_24,
            after_48,
            after_72,
        )

        fingerprint_confidence = round(
            self._number(
                fingerprint.get(
                    "fingerprint_confidence_score"
                )
            )
        )
        analysis_confidence = round(
            self._number(
                detailed.get(
                    "analysis_confidence_score"
                )
            )
        )
        confidence = round(
            mean(
                value
                for value in (
                    fingerprint_confidence,
                    analysis_confidence,
                )
                if value > 0
            )
        ) if (
            fingerprint_confidence > 0
            or analysis_confidence > 0
        ) else 0

        learning_allowed = bool(
            confidence >= 70
            and before is not None
            and any(
                value is not None
                for value in (
                    after_24,
                    after_48,
                    after_72,
                )
            )
        )

        if context.get("exclude_from_learning"):
            learning_allowed = False

        return FusedActivityResponse(
            activity_id=activity_id,
            activity_date=activity_date,
            original_sport=original_sport,
            canonical_sport=canonical_sport,
            session_type=str(
                context.get("session_type")
                or (
                    detailed.get("dominant_work_type")
                    if (
                        canonical_sport == "running"
                        and detailed.get("dominant_work_type")
                        not in (None, "unknown")
                    )
                    else fingerprint.get(
                        "session_type",
                        "unknown",
                    )
                )
            ),
            duration_minutes=round(duration, 1),
            distance_km=round(distance, 2),
            elevation_gain_m=round(elevation, 1),
            physiological_load_score=round(
                physiological,
                1,
            ),
            biomechanical_load_score=round(
                biomechanical,
                1,
            ),
            intensity_score=round(intensity, 1),
            session_load_units=session_load,
            readiness_before=before,
            readiness_24h=after_24,
            readiness_48h=after_48,
            readiness_72h=after_72,
            response_24h=self._difference(
                after_24,
                before,
            ),
            response_48h=self._difference(
                after_48,
                before,
            ),
            response_72h=self._difference(
                after_72,
                before,
            ),
            recovered_within_hours=recovered,
            user_declared_type=declared_type,
            user_context=str(
                context.get("notes", "")
            ),
            confidence_score=confidence,
            automatic_learning_allowed=learning_allowed,
        )

    def _readiness_by_day(
        self,
        snapshots: list[DailyRecoverySnapshot],
    ) -> dict[date, float]:
        adapter = GarminRecoveryAdapter()
        engine = PhysiologyEngine()
        values: dict[date, float] = {}

        for snapshot in snapshots:
            physiology_input = adapter.build_input(
                snapshot,
                snapshots,
            )
            result = engine.analyze(
                physiology_input
            )
            values[snapshot.day] = round(
                result.readiness_score,
                1,
            )

        return values

    def _sport_summaries(
        self,
        activities: list[FusedActivityResponse],
    ) -> list[SportResponseSummary]:
        sports = sorted({
            item.canonical_sport
            for item in activities
        })
        summaries: list[SportResponseSummary] = []

        for sport in sports:
            items = [
                item
                for item in activities
                if item.canonical_sport == sport
            ]
            response_24 = [
                item.response_24h
                for item in items
                if item.response_24h is not None
            ]
            response_48 = [
                item.response_48h
                for item in items
                if item.response_48h is not None
            ]
            recovery_hours = [
                item.recovered_within_hours
                for item in items
                if item.recovered_within_hours is not None
            ]
            confidence_values = [
                item.confidence_score
                for item in items
                if item.confidence_score > 0
            ]

            summaries.append(
                SportResponseSummary(
                    sport=sport,
                    activity_count=len(items),
                    total_duration_hours=round(
                        sum(
                            item.duration_minutes
                            for item in items
                        )
                        / 60,
                        1,
                    ),
                    total_distance_km=round(
                        sum(
                            item.distance_km
                            for item in items
                        ),
                        1,
                    ),
                    average_session_load=round(
                        mean(
                            item.session_load_units
                            for item in items
                        ),
                        1,
                    ),
                    average_response_24h=(
                        round(mean(response_24), 1)
                        if response_24
                        else None
                    ),
                    average_response_48h=(
                        round(mean(response_48), 1)
                        if response_48
                        else None
                    ),
                    average_recovery_hours=(
                        round(mean(recovery_hours), 1)
                        if recovery_hours
                        else None
                    ),
                    confidence_score=(
                        round(mean(confidence_values))
                        if confidence_values
                        else 0
                    ),
                )
            )

        return summaries

    @staticmethod
    def _recovery_hours(
        before: Optional[float],
        after_24: Optional[float],
        after_48: Optional[float],
        after_72: Optional[float],
    ) -> Optional[int]:
        if before is None:
            return None

        acceptable = before - 3.0
        for hours, value in (
            (24, after_24),
            (48, after_48),
            (72, after_72),
        ):
            if value is not None and value >= acceptable:
                return hours

        return None

    @staticmethod
    def _difference(
        value: Optional[float],
        reference: Optional[float],
    ) -> Optional[float]:
        if value is None or reference is None:
            return None
        return round(value - reference, 1)

    @staticmethod
    def _number(
        value: Any,
        *,
        fallback: Any = None,
    ) -> float:
        selected = value
        if selected is None:
            selected = fallback
        try:
            return float(selected or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _optional_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip().lower()
        return text or None

    @staticmethod
    def _explanations(
        activities: list[FusedActivityResponse],
        sports: list[SportResponseSummary],
        acute_load: float,
        chronic_load: float,
        ratio: Optional[float],
    ) -> list[str]:
        explanations = [
            (
                f"{len(activities)} activités ont été "
                "reliées à la récupération quotidienne."
            ),
            (
                f"Charge Atlas sur 7 jours : "
                f"{acute_load:.1f} unités."
            ),
            (
                f"Charge hebdomadaire de référence sur "
                f"28 jours : {chronic_load:.1f} unités."
            ),
        ]

        if ratio is not None:
            explanations.append(
                f"Ratio descriptif 7/28 jours : {ratio:.2f}."
            )

        cycling = next(
            (
                item
                for item in sports
                if item.sport == "cycling"
            ),
            None,
        )
        if cycling is not None:
            explanations.append(
                (
                    f"{cycling.activity_count} sorties vélo "
                    f"représentent "
                    f"{cycling.total_duration_hours:.1f} h "
                    "de charge aérobie croisée."
                )
            )

        altitude = [
            item
            for item in activities
            if item.elevation_gain_m >= 800
        ]
        if altitude:
            explanations.append(
                (
                    f"{len(altitude)} activité(s) à fort "
                    "dénivelé nécessitent une analyse "
                    "spécifique de récupération."
                )
            )

        return explanations

    @staticmethod
    def _warnings(
        activities: list[FusedActivityResponse],
        coverage: float,
        ratio: Optional[float],
    ) -> list[str]:
        warnings: list[str] = []

        if coverage < 70:
            warnings.append(
                (
                    "Couverture Wellness insuffisante pour "
                    "certaines conclusions individuelles."
                )
            )

        excluded = sum(
            1
            for item in activities
            if not item.automatic_learning_allowed
        )
        if excluded:
            warnings.append(
                (
                    f"{excluded} activité(s) ne seront pas "
                    "utilisées automatiquement pour "
                    "l'apprentissage."
                )
            )

        if ratio is None:
            warnings.append(
                "Ratio 7/28 jours non calculable."
            )

        warnings.append(
            (
                "Le ratio de charge est descriptif et ne doit "
                "pas être utilisé seul pour prédire une blessure."
            )
        )

        return warnings