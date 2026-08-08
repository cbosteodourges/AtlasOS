"""Catalogue initial des protocoles scientifiques Atlas Research."""

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


def build_hill_sprints_protocol() -> TrainingResearchProtocol:
    """Construit le protocole court de sprints en côte."""
    return TrainingResearchProtocol(
        protocol_id="hill_sprints_v1",
        version="1.0",
        title="Sprints courts en côte",
        workout_type_key="hill_sprints",
        summary=(
            "Efforts très courts en montée avec récupération complète, "
            "destinés au recrutement neuromusculaire et à la puissance."
        ),
        objectives=[
            "Développer la puissance neuromusculaire",
            "Améliorer la capacité d'accélération",
            "Stimuler la technique de poussée",
        ],
        blocks=[
            ProtocolBlockDefinition(
                name="Sprints en côte",
                repetitions=8,
                duration_seconds=10,
                recovery_seconds=90,
                intensity_basis="effort_maximal_controle",
                intensity_min_percent=95,
                intensity_max_percent=100,
                intensity_pattern=(
                    IntensityPattern.HILL_ACCELERATION
                ),
                gradient_min_percent=6,
                gradient_max_percent=10,
                instructions=(
                    "Accélération progressive, posture haute et arrêt "
                    "de la série si la technique ou la vitesse se dégrade."
                ),
            )
        ],
        applicability=ProtocolApplicability(
            suitable_phases=["base", "development", "specific"],
            suitable_goal_distances_km=[5.0, 10.0, 21.1],
            suitable_athlete_levels=[
                "recreational",
                "competitive",
                "advanced",
            ],
            minimum_sessions_per_week=3,
            maximum_sessions_per_week=1,
            minimum_recovery_hours=48,
            maximum_recovery_hours=72,
            required_metrics=[
                "pain_status",
                "biomechanical_tolerance",
            ],
            contraindications=[
                "douleur_achille_active",
                "douleur_mollet_active",
                "douleur_ischio_jambier_active",
                "fatigue_neuromusculaire_elevee",
            ],
        ),
        expected_adaptations=[
            "Puissance des membres inférieurs",
            "Recrutement neuromusculaire",
            "Économie de course potentiellement améliorée",
        ],
        known_risks=[
            "Charge élevée sur le complexe suro-achillien",
            "Risque musculaire si échauffement insuffisant",
        ],
        references=[
            ResearchReference(
                title=(
                    "The effects of uphill vs. level-grade "
                    "high-intensity interval training"
                ),
                year=2013,
                authors="Ferley DD et al.",
                journal="Journal of Strength and Conditioning Research",
                url="https://pubmed.ncbi.nlm.nih.gov/22996027/",
                evidence_level=EvidenceLevel.RANDOMIZED_TRIAL,
            )
        ],
        evidence_confidence_score=72,
        last_reviewed_at=date(2026, 8, 8),
        research_notes=[
            (
                "La littérature soutient l'entraînement intense en côte, "
                "mais le format Atlas de 10 secondes reste une "
                "prescription prudente à individualiser."
            )
        ],
    )


def build_mixed_threshold_vo2_protocol() -> TrainingResearchProtocol:
    """Construit une séance associant seuil et travail VO2."""
    return TrainingResearchProtocol(
        protocol_id="mixed_threshold_vo2_v1",
        version="1.0",
        title="Séance mixte seuil et VO2",
        workout_type_key="mixed_threshold_vo2",
        summary=(
            "Association d'un bloc au seuil et d'un bloc VO2 dans une "
            "même séance, réservée aux sportifs suffisamment entraînés."
        ),
        objectives=[
            "Développer la vitesse soutenable au seuil",
            "Stimuler la consommation maximale d'oxygène",
            "Préparer les changements d'intensité en compétition",
        ],
        blocks=[
            ProtocolBlockDefinition(
                name="Intervalles au seuil",
                repetitions=3,
                duration_seconds=360,
                recovery_seconds=120,
                intensity_basis="individual_threshold_speed",
                intensity_min_percent=95,
                intensity_max_percent=100,
                intensity_pattern=IntensityPattern.CONSTANT,
                instructions=(
                    "Maintenir une intensité contrôlée sans dépasser "
                    "durablement le seuil individuel."
                ),
            ),
            ProtocolBlockDefinition(
                name="Intervalles VO2",
                repetitions=4,
                duration_seconds=120,
                recovery_seconds=120,
                intensity_basis="vma",
                intensity_min_percent=95,
                intensity_max_percent=100,
                intensity_pattern=IntensityPattern.CONSTANT,
                instructions=(
                    "Conserver une foulée stable et interrompre le bloc "
                    "si la qualité mécanique se détériore."
                ),
            ),
        ],
        applicability=ProtocolApplicability(
            suitable_phases=["development", "specific"],
            suitable_goal_distances_km=[5.0, 10.0, 21.1],
            suitable_athlete_levels=["competitive", "advanced"],
            minimum_sessions_per_week=4,
            maximum_sessions_per_week=1,
            minimum_recovery_hours=48,
            maximum_recovery_hours=72,
            required_metrics=[
                "vma",
                "individual_threshold_speed",
                "recovery_status",
            ],
            contraindications=[
                "fatigue_elevee",
                "recuperation_incomplete",
                "douleur_active",
            ],
        ),
        expected_adaptations=[
            "Amélioration de la vitesse au seuil",
            "Stimulation de la VO2max",
            "Tolérance aux variations d'intensité",
        ],
        known_risks=[
            "Charge physiologique élevée",
            "Dérive excessive si le seuil est mal estimé",
        ],
        references=[
            ResearchReference(
                title=(
                    "Aerobic high-intensity intervals improve VO2max "
                    "more than moderate training"
                ),
                year=2007,
                authors="Helgerud J et al.",
                journal="Medicine and Science in Sports and Exercise",
                url="https://pubmed.ncbi.nlm.nih.gov/17414804/",
                evidence_level=EvidenceLevel.RANDOMIZED_TRIAL,
            )
        ],
        evidence_confidence_score=76,
        last_reviewed_at=date(2026, 8, 8),
        research_notes=[
            (
                "Le seuil et les intervalles VO2 sont soutenus "
                "séparément. Leur combinaison dans une même séance "
                "est une construction Atlas à surveiller."
            )
        ],
    )


def build_triangular_vo2_protocol() -> TrainingResearchProtocol:
    """Construit le protocole Atlas à intensité triangulaire."""
    return TrainingResearchProtocol(
        protocol_id="triangular_vo2_v1",
        version="1.0",
        title="Intervalles VO2 triangulaires",
        workout_type_key="triangular_vo2",
        summary=(
            "Intervalles dont l'intensité augmente puis diminue afin "
            "de moduler la contrainte sans augmenter le travail total."
        ),
        objectives=[
            "Accumuler du temps à haute consommation d'oxygène",
            "Travailler les transitions d'allure",
            "Limiter la monotonie d'un intervalle constant",
        ],
        blocks=[
            ProtocolBlockDefinition(
                name="Intervalles triangulaires",
                repetitions=5,
                duration_seconds=180,
                recovery_seconds=120,
                intensity_basis="vma",
                intensity_min_percent=90,
                intensity_max_percent=105,
                intensity_pattern=IntensityPattern.TRIANGULAR,
                instructions=(
                    "Augmenter progressivement jusqu'au milieu de "
                    "l'intervalle, puis revenir progressivement à "
                    "l'intensité initiale."
                ),
            )
        ],
        applicability=ProtocolApplicability(
            suitable_phases=["development", "specific"],
            suitable_goal_distances_km=[5.0, 10.0],
            suitable_athlete_levels=["competitive", "advanced"],
            minimum_sessions_per_week=4,
            maximum_sessions_per_week=1,
            minimum_recovery_hours=48,
            maximum_recovery_hours=72,
            required_metrics=["vma", "recovery_status"],
            contraindications=[
                "fatigue_elevee",
                "recuperation_incomplete",
                "douleur_active",
            ],
        ),
        expected_adaptations=[
            "Temps prolongé à haute intensité",
            "Adaptation aux changements d'allure",
        ],
        known_risks=[
            "Départ trop rapide",
            "Pic d'intensité mal toléré",
        ],
        references=[
            ResearchReference(
                title=(
                    "Similar time near VO2max regardless of work rate "
                    "manipulation in work-matched interval training"
                ),
                year=2021,
                authors="Bossi AH et al.",
                url="https://pubmed.ncbi.nlm.nih.gov/34261134/",
                evidence_level=EvidenceLevel.CROSSOVER_TRIAL,
            )
        ],
        evidence_confidence_score=58,
        last_reviewed_at=date(2026, 8, 8),
        research_notes=[
            (
                "Le format triangulaire est un modèle expérimental "
                "Atlas. Les preuves disponibles concernent surtout "
                "la modulation de puissance à travail total égal."
            )
        ],
    )


def build_default_training_protocol_registry(
) -> TrainingProtocolRegistry:
    """Construit le registre initial validé par Atlas Research."""
    registry = TrainingProtocolRegistry()

    for protocol in (
        build_hill_sprints_protocol(),
        build_mixed_threshold_vo2_protocol(),
        build_triangular_vo2_protocol(),
    ):
        registry.register(protocol)

    return registry