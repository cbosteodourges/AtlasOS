"""
ATLAS OS
Construction et apprentissage des empreintes de séances.
"""

import re
from collections import defaultdict
from statistics import mean
from typing import Dict, List, Optional

from .longitudinal_models import (
    LongitudinalActivity,
)
from .session_fingerprint import (
    AthleteSessionLearning,
    SessionFingerprint,
    SessionTypeEffectiveness,
)


class SessionFingerprintBuilder:
    """
    Transforme les activités en empreintes comparables.

    Les scores restent explicables et seront progressivement
    personnalisés avec les réponses à 24–72 heures.
    """

    def build(
        self,
        activity: LongitudinalActivity,
    ) -> SessionFingerprint:
        """Construit l'empreinte d'une activité."""
        session_type, reasons = (
            self._classify_session(activity)
        )
        missing_data = self._missing_data(
            activity
        )

        return SessionFingerprint(
            activity_id=activity.atlas_id,
            start_time=activity.start_time,
            sport=self._sport(activity),
            session_type=session_type,
            distance_km=round(
                activity.distance_km,
                2,
            ),
            duration_minutes=round(
                activity.duration_minutes,
                1,
            ),
            elevation_gain_m=round(
                activity.elevation_gain_m or 0.0,
                1,
            ),
            pace_seconds_per_km=(
                self._round_optional(
                    activity.pace_seconds_per_km,
                    1,
                )
            ),
            average_speed_kmh=(
                self._round_optional(
                    activity.average_speed_kmh,
                    2,
                )
            ),
            average_heart_rate_bpm=(
                activity.average_heart_rate_bpm
            ),
            maximum_heart_rate_bpm=(
                activity.maximum_heart_rate_bpm
            ),
            aerobic_efficiency=(
                self._round_optional(
                    activity.aerobic_efficiency,
                    4,
                )
            ),
            training_load=activity.training_load,
            perceived_effort_1_to_10=(
                activity.recovery
                .perceived_effort_1_to_10
            ),
            feeling_score_0_to_100=(
                activity.recovery
                .feeling_score_0_to_100
            ),
            aerobic_training_effect=(
                activity.recovery
                .aerobic_training_effect
            ),
            anaerobic_training_effect=(
                activity.recovery
                .anaerobic_training_effect
            ),
            body_battery_impact=(
                activity.recovery
                .body_battery_impact
            ),
            temperature_c=(
                activity.environment
                .average_temperature_c
            ),
            external_load_score=(
                self._external_load_score(
                    activity
                )
            ),
            internal_load_score=(
                self._internal_load_score(
                    activity
                )
            ),
            intensity_score=(
                self._intensity_score(
                    activity,
                    session_type,
                )
            ),
            immediate_response_score=(
                self._immediate_response_score(
                    activity
                )
            ),
            data_quality_score=(
                activity.data_quality_score
            ),
            fingerprint_confidence_score=(
                self._confidence_score(
                    activity
                )
            ),
            classification_reasons=reasons,
            missing_data=missing_data,
        )

    def build_learning(
        self,
        athlete_id: str,
        activities: List[LongitudinalActivity],
    ) -> AthleteSessionLearning:
        """Construit la mémoire individuelle des séances."""
        fingerprints = [
            self.build(activity)
            for activity in sorted(
                activities,
                key=lambda item: item.start_time,
            )
        ]

        grouped: Dict[
            str,
            List[SessionFingerprint],
        ] = defaultdict(list)

        for fingerprint in fingerprints:
            grouped[
                fingerprint.session_type
            ].append(fingerprint)

        effectiveness = [
            self._summarize_type(
                session_type,
                values,
            )
            for session_type, values
            in sorted(grouped.items())
        ]

        global_confidence = (
            round(
                mean(
                    fingerprint
                    .fingerprint_confidence_score
                    for fingerprint
                    in fingerprints
                )
            )
            if fingerprints
            else 0
        )

        learning = AthleteSessionLearning(
            athlete_id=athlete_id,
            fingerprint_count=len(
                fingerprints
            ),
            fingerprints=fingerprints,
            session_type_effectiveness=(
                effectiveness
            ),
            global_confidence_score=(
                global_confidence
            ),
        )

        self._build_conclusions(
            learning
        )

        return learning

    def _summarize_type(
        self,
        session_type: str,
        fingerprints: List[SessionFingerprint],
    ) -> SessionTypeEffectiveness:
        immediate_responses = [
            fingerprint.immediate_response_score
            for fingerprint in fingerprints
            if (
                fingerprint
                .immediate_response_score
                is not None
            )
        ]
        perceived_efforts = [
            fingerprint.perceived_effort_1_to_10
            for fingerprint in fingerprints
            if (
                fingerprint
                .perceived_effort_1_to_10
                is not None
            )
        ]
        feeling_scores = [
            fingerprint.feeling_score_0_to_100
            for fingerprint in fingerprints
            if (
                fingerprint
                .feeling_score_0_to_100
                is not None
            )
        ]
        efficiencies = [
            fingerprint.aerobic_efficiency
            for fingerprint in fingerprints
            if (
                fingerprint.aerobic_efficiency
                is not None
            )
        ]

        average_response = self._average(
            immediate_responses
        )
        average_feeling = self._average(
            feeling_scores
        )

        effectiveness_score = (
            self._effectiveness_score(
                average_response,
                average_feeling,
            )
        )
        confidence = self._type_confidence(
            fingerprints
        )

        result = SessionTypeEffectiveness(
            session_type=session_type,
            session_count=len(fingerprints),
            average_distance_km=round(
                mean(
                    fingerprint.distance_km
                    for fingerprint in fingerprints
                ),
                1,
            ),
            average_duration_minutes=round(
                mean(
                    fingerprint.duration_minutes
                    for fingerprint in fingerprints
                ),
                1,
            ),
            average_external_load_score=round(
                mean(
                    fingerprint.external_load_score
                    for fingerprint in fingerprints
                ),
                1,
            ),
            average_internal_load_score=round(
                mean(
                    fingerprint.internal_load_score
                    for fingerprint in fingerprints
                ),
                1,
            ),
            average_intensity_score=round(
                mean(
                    fingerprint.intensity_score
                    for fingerprint in fingerprints
                ),
                1,
            ),
            average_perceived_effort=(
                self._average(
                    perceived_efforts
                )
            ),
            average_feeling_score=(
                average_feeling
            ),
            average_aerobic_efficiency=(
                self._average(
                    efficiencies,
                    digits=4,
                )
            ),
            average_immediate_response_score=(
                average_response
            ),
            effectiveness_score=(
                effectiveness_score
            ),
            confidence_score=confidence,
        )

        self._describe_effectiveness(
            result
        )

        return result

    def _classify_session(
        self,
        activity: LongitudinalActivity,
    ) -> tuple[str, List[str]]:
        title = activity.title.lower()
        reasons: List[str] = []

        if not self._is_running(activity):
            sport = self._sport(activity)
            reasons.append(
                "Classification issue du type "
                f"d'activité : {sport}."
            )
            return sport, reasons

        if (
            "longue course" in title
            or "sortie longue" in title
            or "long run" in title
            or activity.distance_km >= 14
        ):
            reasons.append(
                "Distance ou intitulé compatible "
                "avec une sortie longue."
            )
            return "long_run", reasons

        if "seuil" in title:
            reasons.append(
                "Le titre identifie un travail au seuil."
            )
            return "threshold", reasons

        if (
            "vo2" in title
            or "vma" in title
        ):
            reasons.append(
                "Le titre identifie un travail VO2 max "
                "ou VMA."
            )
            return "vo2", reasons

        if "tempo" in title:
            reasons.append(
                "Le titre identifie un travail tempo."
            )
            return "tempo", reasons

        if (
            "fraction" in title
            or "interval" in title
            or re.search(
                r"\d+\s*x\s*\d+",
                title,
            )
        ):
            reasons.append(
                "Le titre identifie une séance "
                "fractionnée."
            )
            return "interval", reasons

        if (
            "récup" in title
            or "recup" in title
            or "recovery" in title
        ):
            reasons.append(
                "Le titre identifie une séance "
                "de récupération."
            )
            return "recovery", reasons

        reasons.append(
            "Aucun marqueur spécifique : "
            "séance classée en endurance facile."
        )
        return "easy", reasons

    @staticmethod
    def _external_load_score(
        activity: LongitudinalActivity,
    ) -> int:
        duration_component = min(
            activity.duration_minutes / 120,
            1.0,
        ) * 40
        distance_component = min(
            activity.distance_km / 20,
            1.0,
        ) * 40
        elevation_component = min(
            (activity.elevation_gain_m or 0)
            / 500,
            1.0,
        ) * 20

        return round(
            duration_component
            + distance_component
            + elevation_component
        )

    @staticmethod
    def _internal_load_score(
        activity: LongitudinalActivity,
    ) -> int:
        components: List[float] = []

        if activity.training_load is not None:
            components.append(
                min(
                    activity.training_load / 250,
                    1.0,
                )
                * 35
            )

        if (
            activity.average_heart_rate_bpm
            is not None
            and activity.maximum_heart_rate_bpm
            is not None
            and activity.maximum_heart_rate_bpm > 0
        ):
            components.append(
                min(
                    activity.average_heart_rate_bpm
                    / activity.maximum_heart_rate_bpm,
                    1.0,
                )
                * 20
            )

        aerobic_effect = (
            activity.recovery
            .aerobic_training_effect
        )
        if aerobic_effect is not None:
            components.append(
                min(
                    aerobic_effect / 5,
                    1.0,
                )
                * 20
            )

        perceived_effort = (
            activity.recovery
            .perceived_effort_1_to_10
        )
        if perceived_effort is not None:
            components.append(
                min(
                    perceived_effort / 10,
                    1.0,
                )
                * 25
            )

        return round(sum(components))

    @staticmethod
    def _intensity_score(
        activity: LongitudinalActivity,
        session_type: str,
    ) -> int:
        base_scores = {
            "recovery": 15,
            "easy": 25,
            "long_run": 40,
            "tempo": 60,
            "threshold": 70,
            "interval": 80,
            "vo2": 85,
        }
        score = base_scores.get(
            session_type,
            35,
        )

        perceived_effort = (
            activity.recovery
            .perceived_effort_1_to_10
        )
        if perceived_effort is not None:
            score = round(
                score * 0.7
                + perceived_effort * 10 * 0.3
            )

        anaerobic_effect = (
            activity.recovery
            .anaerobic_training_effect
        )
        if anaerobic_effect is not None:
            score += round(
                min(
                    anaerobic_effect / 5,
                    1.0,
                )
                * 10
            )

        return min(max(score, 0), 100)

    @staticmethod
    def _immediate_response_score(
        activity: LongitudinalActivity,
    ) -> Optional[int]:
        feeling = (
            activity.recovery
            .feeling_score_0_to_100
        )
        battery_impact = (
            activity.recovery
            .body_battery_impact
        )

        components: List[float] = []

        if feeling is not None:
            components.append(
                min(max(feeling, 0), 100)
            )

        if battery_impact is not None:
            battery_score = (
                100
                - min(
                    abs(battery_impact) * 2,
                    100,
                )
            )
            components.append(
                battery_score
            )

        if not components:
            return None

        return round(mean(components))

    @staticmethod
    def _confidence_score(
        activity: LongitudinalActivity,
    ) -> int:
        score = 20

        if activity.data_quality_score >= 70:
            score += 20

        if (
            activity.average_speed_kmh is not None
            and activity.average_heart_rate_bpm
            is not None
        ):
            score += 15

        if (
            activity.training_load is not None
            and activity.recovery
            .aerobic_training_effect
            is not None
        ):
            score += 15

        if (
            activity.recovery
            .perceived_effort_1_to_10
            is not None
            and activity.recovery
            .feeling_score_0_to_100
            is not None
        ):
            score += 20

        if (
            activity.recovery
            .body_battery_impact
            is not None
        ):
            score += 10

        return min(score, 100)

    @staticmethod
    def _missing_data(
        activity: LongitudinalActivity,
    ) -> List[str]:
        missing: List[str] = []

        if activity.training_load is None:
            missing.append(
                "Charge d'entraînement"
            )

        if (
            activity.recovery
            .perceived_effort_1_to_10
            is None
        ):
            missing.append(
                "Effort perçu"
            )

        if (
            activity.recovery
            .feeling_score_0_to_100
            is None
        ):
            missing.append(
                "Ressenti"
            )

        if (
            activity.recovery
            .body_battery_impact
            is None
        ):
            missing.append(
                "Impact Body Battery"
            )

        if (
            activity.environment
            .average_temperature_c
            is None
        ):
            missing.append(
                "Température"
            )

        return missing

    @staticmethod
    def _effectiveness_score(
        average_response: Optional[float],
        average_feeling: Optional[float],
    ) -> int:
        values = [
            value
            for value in {
                average_response,
                average_feeling,
            }
            if value is not None
        ]

        if not values:
            return 0

        return round(mean(values))

    @staticmethod
    def _type_confidence(
        fingerprints: List[SessionFingerprint],
    ) -> int:
        average_confidence = mean(
            fingerprint.fingerprint_confidence_score
            for fingerprint in fingerprints
        )
        sample_bonus = min(
            len(fingerprints) * 5,
            20,
        )

        return min(
            round(
                average_confidence * 0.8
                + sample_bonus
            ),
            100,
        )

    @staticmethod
    def _describe_effectiveness(
        result: SessionTypeEffectiveness,
    ) -> None:
        if (
            result.average_feeling_score
            is not None
            and result.average_feeling_score >= 75
        ):
            result.positive_signals.append(
                "Ressenti moyen favorable après ce type "
                "de séance."
            )

        if (
            result.average_immediate_response_score
            is not None
            and result
            .average_immediate_response_score >= 70
        ):
            result.positive_signals.append(
                "Réponse immédiate généralement bien "
                "tolérée."
            )

        if (
            result.average_perceived_effort
            is not None
            and result.average_perceived_effort >= 8
        ):
            result.warning_signals.append(
                "Effort perçu moyen élevé."
            )

        if result.session_count < 3:
            result.warning_signals.append(
                "Échantillon encore trop limité pour "
                "une conclusion solide."
            )

    @staticmethod
    def _build_conclusions(
        learning: AthleteSessionLearning,
    ) -> None:
        if not learning.fingerprints:
            learning.conclusions.append(
                "Aucune séance exploitable."
            )
            return

        learning.conclusions.append(
            f"{learning.fingerprint_count} séance(s) "
            "transformée(s) en empreintes comparables."
        )

        eligible_results = [
            result
            for result
            in learning.session_type_effectiveness
            if (
                result.session_count >= 3
                and result.average_perceived_effort
                is not None
                and result.average_feeling_score
                is not None
                and result.confidence_score >= 70
            )
        ]

        if not eligible_results:
            learning.conclusions.append(
                "RPE et ressenti insuffisants pour identifier "
                "le type de séance réellement le plus efficace."
            )
            learning.conclusions.append(
                "Les scores actuels décrivent uniquement "
                "une tolérance immédiate provisoire."
            )
            return

        best = max(
            eligible_results,
            key=lambda result: (
                result.effectiveness_score,
                result.confidence_score,
            ),
        )
        learning.conclusions.append(
            "Meilleure réponse immédiate documentée : "
            f"{best.session_type} "
            f"({best.effectiveness_score}/100, "
            f"confiance {best.confidence_score}/100)."
        )

    @staticmethod
    def _average(
        values: List[float],
        digits: int = 1,
    ) -> Optional[float]:
        if not values:
            return None

        return round(
            mean(values),
            digits,
        )
    @staticmethod
    def _round_optional(
        value: Optional[float],
        digits: int,
    ) -> Optional[float]:
        if value is None:
            return None

        return round(value, digits)

    @staticmethod
    def _sport(
        activity: LongitudinalActivity,
    ) -> str:
        activity_type = (
            activity.activity_type.lower()
        )

        if (
            "running" in activity_type
            or activity_type
            in {
                "ultrafond",
                "ultra_running",
            }
        ):
            return "running"

        if (
            "cycling" in activity_type
            or "cyclisme" in activity_type
            or "biking" in activity_type
            or activity_type in {
                "road",
                "vtt",
                "mountain_biking",
                "gravel_cycling",
            }
        ):
            return "cycling"

        return activity_type or "other"

    @staticmethod
    def _is_running(
        activity: LongitudinalActivity,
    ) -> bool:
        return (
            SessionFingerprintBuilder
            ._sport(activity)
            == "running"
        )
