"""Catalogue isolé du pilote 3+1 et Norwegian Singles."""

from datetime import date

from .training_protocol import (
    EvidenceLevel,
    IntensityPattern,
    ProtocolApplicability,
    ProtocolBlockDefinition,
    ResearchReference,
    TrainingProtocolRegistry,
    TrainingResearchProtocol,
)


NORWEGIAN_GUIDANCE = (
    "Cette séance n'est pas un test. Rester légèrement sous le SV2, "
    "à RPE 5–6/10, et terminer avec la sensation de pouvoir effectuer "
    "encore une répétition. Il vaut mieux être légèrement trop lent "
    "que trop rapide."
)


def _applicability(*, recovery_hours: int = 48) -> ProtocolApplicability:
    return ProtocolApplicability(
        suitable_phases=["development", "specific"],
        suitable_goal_distances_km=[10.0, 21.1, 42.2],
        suitable_athlete_levels=["competitive", "advanced"],
        minimum_sessions_per_week=4,
        maximum_sessions_per_week=1,
        minimum_recovery_hours=recovery_hours,
        maximum_recovery_hours=72,
        required_metrics=[
            "individual_threshold_speed",
            "recovery_status",
            "pain_status",
        ],
        contraindications=[
            "douleur_active",
            "fatigue_elevee",
            "recuperation_incomplete",
        ],
    )


def _subthreshold_protocol(
    *,
    protocol_id: str,
    title: str,
    repetitions: int,
    duration_seconds: int,
    recovery_seconds: int,
) -> TrainingResearchProtocol:
    return TrainingResearchProtocol(
        protocol_id=protocol_id,
        version="pilot-1.0",
        title=title,
        workout_type_key="subthreshold_norwegian",
        summary=(
            "Intervalles sous le SV2 intégrés à une charge globale "
            "plafonnée et pilotés par allure, FC, dérive et ressenti."
        ),
        objectives=[
            "Accumuler du temps sous le seuil sans le dépasser",
            "Développer la clairance et la durabilité aérobie",
            "Limiter la fatigue résiduelle entre les séances",
        ],
        blocks=[
            ProtocolBlockDefinition(
                name=title,
                repetitions=repetitions,
                duration_seconds=duration_seconds,
                recovery_seconds=recovery_seconds,
                intensity_basis="subthreshold_speed",
                intensity_min_percent=90,
                intensity_max_percent=96,
                intensity_pattern=IntensityPattern.CONSTANT,
                instructions=NORWEGIAN_GUIDANCE,
            )
        ],
        applicability=_applicability(),
        expected_adaptations=[
            "Volume métabolique contrôlé",
            "Meilleure stabilité allure–fréquence cardiaque",
            "Tolérance au travail proche du seuil",
        ],
        known_risks=[
            "Dérive au-dessus du SV2 si l'allure devient un objectif rigide",
            "Fatigue cumulative si les trois stimuli hebdomadaires ne sont pas raccourcis",
        ],
        references=[
            ResearchReference(
                title="Norwegian Singles community protocol and wiki",
                year=2026,
                authors="Norwegian Singles Run community",
                url="https://www.reddit.com/r/NorwegianSinglesRun/wiki/index/",
                evidence_level=EvidenceLevel.EMERGING,
            )
        ],
        evidence_confidence_score=62,
        last_reviewed_at=date(2026, 8, 22),
        research_notes=[
            "Protocole pilote Atlas Research, non universel.",
            "Le SV2 reste longitudinal et ne doit jamais être figé.",
        ],
    )


def build_subthreshold_3x10_protocol() -> TrainingResearchProtocol:
    return _subthreshold_protocol(
        protocol_id="subthreshold_3x10",
        title="Norwegian Single · 3 × 10 min",
        repetitions=3,
        duration_seconds=600,
        recovery_seconds=90,
    )


def build_subthreshold_5x6_protocol() -> TrainingResearchProtocol:
    return _subthreshold_protocol(
        protocol_id="subthreshold_5x6",
        title="Norwegian Single · 5 × 6 min",
        repetitions=5,
        duration_seconds=360,
        recovery_seconds=75,
    )


def build_subthreshold_8_to_10x3_protocol() -> TrainingResearchProtocol:
    protocol = _subthreshold_protocol(
        protocol_id="subthreshold_8_to_10x3",
        title="Norwegian Single · 8 à 10 × 3 min",
        repetitions=8,
        duration_seconds=180,
        recovery_seconds=60,
    )
    protocol.research_notes.append(
        "Commencer à 8 répétitions ; 9 puis 10 seulement après validation FIT et ressenti."
    )
    return protocol


def _microdose_protocol(
    *,
    protocol_id: str,
    title: str,
    intensity_basis: str,
    repetitions: int,
    duration_seconds: int,
    recovery_seconds: int,
    gradient_min: float | None = None,
    gradient_max: float | None = None,
    instructions: str,
) -> TrainingResearchProtocol:
    return TrainingResearchProtocol(
        protocol_id=protocol_id,
        version="pilot-1.0",
        title=title,
        workout_type_key="neuromuscular_microdose",
        summary="Microdose technique sans charge lactique significative.",
        objectives=[
            "Préserver la vitesse et la coordination",
            "Stimuler le recrutement neuromusculaire sans fatigue métabolique",
        ],
        blocks=[
            ProtocolBlockDefinition(
                name=title,
                repetitions=repetitions,
                duration_seconds=duration_seconds,
                recovery_seconds=recovery_seconds,
                intensity_basis=intensity_basis,
                intensity_min_percent=85,
                intensity_max_percent=92,
                gradient_min_percent=gradient_min,
                gradient_max_percent=gradient_max,
                instructions=instructions,
            )
        ],
        applicability=_applicability(recovery_hours=24),
        expected_adaptations=["Coordination", "Force spécifique", "Économie de course"],
        known_risks=["Charge musculotendineuse si la technique se dégrade"],
        evidence_confidence_score=58,
        last_reviewed_at=date(2026, 8, 22),
        research_notes=["Réservé à la semaine de consolidation du pilote 3+1."],
    )


def build_hill_neuromuscular_sprints_protocol() -> TrainingResearchProtocol:
    protocol = _microdose_protocol(
        protocol_id="hill_neuromuscular_sprints",
        title="Microdose côte · 6 à 8 répétitions",
        intensity_basis="effort_powerful_technical",
        repetitions=6,
        duration_seconds=12,
        recovery_seconds=150,
        gradient_min=4,
        gradient_max=7,
        instructions="Commencer par 6 × 12 s puis progresser vers 7 et 8 répétitions seulement si la technique reste propre ; récupération complète et arrêt à la première dégradation.",
    )
    protocol.research_notes.append(
        "Progression Atlas : 6 répétitions à la première exposition, puis 7 et 8 après validation de la technique, de la douleur et de la récupération à J+1."
    )
    return protocol


def build_flat_relaxed_strides_protocol() -> TrainingResearchProtocol:
    protocol = _microdose_protocol(
        protocol_id="flat_relaxed_strides",
        title="Lignes droites relâchées · 6 à 8 répétitions",
        intensity_basis="relaxed_max_speed",
        repetitions=6,
        duration_seconds=20,
        recovery_seconds=120,
        instructions="Commencer par 6 × 20 s puis progresser vers 7 et 8 répétitions à 85–92 % de la vitesse maximale, relâché et sans sprint final.",
    )
    protocol.research_notes.append(
        "La progression porte sur le nombre de répétitions, jamais simultanément sur la vitesse."
    )
    return protocol


def build_gentle_downhill_eccentric_protocol() -> TrainingResearchProtocol:
    protocol = _microdose_protocol(
        protocol_id="gentle_downhill_eccentric_intro",
        title="Introduction excentrique en descente douce",
        intensity_basis="controlled_downhill_speed",
        repetitions=4,
        duration_seconds=12,
        recovery_seconds=150,
        gradient_min=-3,
        gradient_max=-2,
        instructions="Surface sèche et régulière, vitesse rapide non maximale, freinage contrôlé et récupération complète.",
    )
    protocol.applicability.contraindications.extend([
        "objectif_route_prioritaire",
        "inexperience_descente",
        "douleur_quadriceps_genou",
    ])
    return protocol


def build_three_plus_one_pilot_registry() -> TrainingProtocolRegistry:
    registry = TrainingProtocolRegistry()
    for protocol in (
        build_subthreshold_3x10_protocol(),
        build_subthreshold_5x6_protocol(),
        build_subthreshold_8_to_10x3_protocol(),
        build_hill_neuromuscular_sprints_protocol(),
        build_flat_relaxed_strides_protocol(),
        build_gentle_downhill_eccentric_protocol(),
    ):
        registry.register(protocol)
    return registry
