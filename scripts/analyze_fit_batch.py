"""
ATLAS OS
Analyse en série des séances Garmin FIT privées.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors import GarminConnector  # noqa: E402
from src.performance import (  # noqa: E402
    AthleteProfile,
    DetailedSessionAnalyzer,
    LongitudinalActivityAdapter,
    PhysiologicalReferences,
    ThresholdEvolutionAnalyzer,
)


def parse_arguments() -> argparse.Namespace:
    """Lit le dossier FIT et les références individuelles."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyse toutes les séances FIT d'un dossier."
        )
    )
    parser.add_argument(
        "--input",
        default="atlas-data/garmin",
        help="Dossier privé contenant les fichiers FIT.",
    )
    parser.add_argument(
        "--vma",
        required=True,
        type=float,
        help="VMA actuelle en km/h.",
    )
    parser.add_argument(
        "--max-hr",
        required=True,
        type=float,
        help="Fréquence cardiaque maximale en bpm.",
    )
    parser.add_argument(
        "--sv2-speed",
        type=float,
        default=None,
        help="Vitesse SV2 actuelle en km/h.",
    )
    parser.add_argument(
        "--sv2-hr",
        type=float,
        default=None,
        help="Fréquence cardiaque SV2 actuelle en bpm.",
    )
    parser.add_argument(
        "--output",
        default=(
            "atlas-data/private/"
            "detailed-fit-batch-analysis.json"
        ),
        help="Fichier JSON privé de sortie.",
    )
    return parser.parse_args()


def build_profile(
    arguments: argparse.Namespace,
) -> AthleteProfile:
    """Construit les références utilisées pour le lot."""
    return AthleteProfile(
        athlete_id="local-athlete",
        declared_level="unknown",
        observed_level="unknown",
        physiological=PhysiologicalReferences(
            maximum_heart_rate_bpm=arguments.max_hr,
            threshold_heart_rate_bpm=arguments.sv2_hr,
            vma_kmh=arguments.vma,
            threshold_speed_kmh=arguments.sv2_speed,
        ),
    )


def analyze_directory(
    input_directory: str,
    profile: AthleteProfile,
) -> tuple[list, list, list]:
    """Décode et analyse toutes les activités FIT."""
    connector = GarminConnector(input_directory)
    connector.connect()
    raw_activities = list(
        connector.fetch_activities()
    )

    adapter = LongitudinalActivityAdapter()
    analyzer = DetailedSessionAnalyzer()

    analyses = []
    analysis_objects = []
    summaries = []
    errors = []

    for raw_activity in raw_activities:
        try:
            normalized = connector.normalize(
                raw_activity
            )
            longitudinal = adapter.adapt(
                normalized
            )
            analysis = analyzer.analyze(
                longitudinal,
                profile,
            )
            manual_lap_count = sum(
                1
                for lap in longitudinal.laps
                if str(
                    lap.get("lap_trigger", "")
                ).lower() == "manual"
            )
            threshold_names = [
                observation.threshold_name
                for observation in (
                    analysis.threshold_observations
                )
            ]

            summaries.append(
                {
                    "activity_id": longitudinal.atlas_id,
                    "start_time": (
                        longitudinal.start_time.isoformat()
                    ),
                    "sport": (
                        longitudinal.activity_type
                    ),
                    "distance_km": round(
                        longitudinal.distance_km,
                        2,
                    ),
                    "duration_minutes": round(
                        longitudinal.duration_minutes,
                        1,
                    ),
                    "sample_count": len(
                        longitudinal.samples
                    ),
                    "lap_count": len(
                        longitudinal.laps
                    ),
                    "manual_lap_count": (
                        manual_lap_count
                    ),
                    "block_count": len(
                        analysis.blocks
                    ),
                    "dominant_work_type": (
                        analysis.dominant_work_type
                    ),
                    "physiological_load_score": (
                        analysis
                        .physiological_load_score
                    ),
                    "biomechanical_load_score": (
                        analysis
                        .biomechanical_load_score
                    ),
                    "confidence_score": (
                        analysis
                        .analysis_confidence_score
                    ),
                    "threshold_observations": (
                        threshold_names
                    ),
                }
            )
            analyses.append(asdict(analysis))
            analysis_objects.append(analysis)

        except Exception as error:
            errors.append(
                {
                    "activity_id": (
                        raw_activity.external_id
                    ),
                    "error": str(error),
                }
            )

    summaries.sort(
        key=lambda item: item["start_time"]
    )

    evolved_profile = ThresholdEvolutionAnalyzer().update(
        profile,
        analysis_objects,
    )

    return (
        analyses,
        summaries,
        errors,
        evolved_profile,
    )


def build_global_summary(
    summaries: list,
    analyses: list,
    errors: list,
) -> dict:
    """Produit une vision compacte du lot analysé."""
    dominant_types = Counter(
        item["dominant_work_type"]
        for item in summaries
    )
    block_types = Counter(
        block["block_type"]
        for analysis in analyses
        for block in analysis["blocks"]
    )

    return {
        "activity_count": len(summaries),
        "error_count": len(errors),
        "total_sample_count": sum(
            item["sample_count"]
            for item in summaries
        ),
        "total_lap_count": sum(
            item["lap_count"]
            for item in summaries
        ),
        "manual_lap_activity_count": sum(
            1
            for item in summaries
            if item["manual_lap_count"] > 0
        ),
        "average_block_count": round(
            mean(
                item["block_count"]
                for item in summaries
            ),
            1,
        ) if summaries else 0,
        "average_confidence_score": round(
            mean(
                item["confidence_score"]
                for item in summaries
            ),
            1,
        ) if summaries else 0,
        "dominant_work_types": dict(
            dominant_types.most_common()
        ),
        "detected_block_types": dict(
            block_types.most_common()
        ),
        "sv1_observation_count": sum(
            1
            for item in summaries
            if "sv1" in item[
                "threshold_observations"
            ]
        ),
        "sv2_observation_count": sum(
            1
            for item in summaries
            if "sv2" in item[
                "threshold_observations"
            ]
        ),
    }


def threshold_to_dict(threshold) -> dict:
    """Sérialise un seuil évolutif et son historique."""
    return {
        "threshold_name": threshold.threshold_name,
        "speed_kmh": threshold.speed_kmh,
        "heart_rate_bpm": threshold.heart_rate_bpm,
        "minimum_speed_kmh": (
            threshold.minimum_speed_kmh
        ),
        "maximum_speed_kmh": (
            threshold.maximum_speed_kmh
        ),
        "minimum_heart_rate_bpm": (
            threshold.minimum_heart_rate_bpm
        ),
        "maximum_heart_rate_bpm": (
            threshold.maximum_heart_rate_bpm
        ),
        "confidence_score": (
            threshold.confidence_score
        ),
        "observation_count": (
            threshold.observation_count
        ),
        "trend": threshold.trend,
        "last_updated_at": (
            threshold.last_updated_at.isoformat()
            if threshold.last_updated_at
            else None
        ),
        "evidence": threshold.evidence,
        "history": [
            {
                "recorded_at": (
                    item.recorded_at.isoformat()
                ),
                "speed_kmh": item.speed_kmh,
                "heart_rate_bpm": (
                    item.heart_rate_bpm
                ),
                "confidence_score": (
                    item.confidence_score
                ),
                "observation_count": (
                    item.observation_count
                ),
            }
            for item in threshold.history
        ],
    }


def write_result(
    destination_path: str,
    global_summary: dict,
    summaries: list,
    analyses: list,
    errors: list,
    evolved_profile: AthleteProfile,
    arguments: argparse.Namespace,
) -> Path:
    """Enregistre les résultats dans un JSON privé."""
    destination = Path(destination_path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "generated_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "references": {
            "vma_kmh": arguments.vma,
            "maximum_heart_rate_bpm": (
                arguments.max_hr
            ),
            "sv2_speed_kmh": (
                arguments.sv2_speed
            ),
            "sv2_heart_rate_bpm": (
                arguments.sv2_hr
            ),
        },
        "global_summary": global_summary,
        "evolving_thresholds": {
            "sv1": threshold_to_dict(
                evolved_profile.physiological.sv1
            ),
            "sv2": threshold_to_dict(
                evolved_profile.physiological.sv2
            ),
        },
        "activities": summaries,
        "analyses": analyses,
        "errors": errors,
    }

    with destination.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            payload,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    return destination


def display_summary(
    global_summary: dict,
    destination: Path,
) -> None:
    """Affiche seulement les résultats essentiels."""
    print()
    print("ANALYSE EN SÉRIE DES SÉANCES FIT")
    print("=" * 64)
    print(
        f"Séances analysées : "
        f"{global_summary['activity_count']}"
    )
    print(
        f"Erreurs : "
        f"{global_summary['error_count']}"
    )
    print(
        f"Points détaillés : "
        f"{global_summary['total_sample_count']}"
    )
    print(
        f"Tours FIT : "
        f"{global_summary['total_lap_count']}"
    )
    print(
        f"Séances avec tours manuels : "
        f"{global_summary['manual_lap_activity_count']}"
    )
    print(
        f"Nombre moyen de blocs : "
        f"{global_summary['average_block_count']}"
    )
    print(
        f"Confiance moyenne : "
        f"{global_summary['average_confidence_score']}/100"
    )
    print(
        f"Observations SV1 : "
        f"{global_summary['sv1_observation_count']}"
    )
    print(
        f"Observations SV2 : "
        f"{global_summary['sv2_observation_count']}"
    )
    print()
    print("Types de travail dominants :")
    for work_type, count in (
        global_summary[
            "dominant_work_types"
        ].items()
    ):
        print(f"- {work_type} : {count}")
    print()
    print(f"Analyse privée : {destination}")


def main() -> None:
    """Lance l'analyse détaillée du lot FIT."""
    arguments = parse_arguments()
    profile = build_profile(arguments)

    (
        analyses,
        summaries,
        errors,
        evolved_profile,
    ) = analyze_directory(
        arguments.input,
        profile,
    )
    global_summary = build_global_summary(
        summaries,
        analyses,
        errors,
    )
    destination = write_result(
        arguments.output,
        global_summary,
        summaries,
        analyses,
        errors,
        evolved_profile,
        arguments,
    )
    display_summary(
        global_summary,
        destination,
    )

    print()
    print("SEUILS ÉVOLUTIFS CONSOLIDÉS")
    print("-" * 64)

    for threshold in (
        evolved_profile.physiological.sv1,
        evolved_profile.physiological.sv2,
    ):
        speed = (
            f"{threshold.speed_kmh:.2f} km/h"
            if threshold.speed_kmh is not None
            else "non validée"
        )
        heart_rate = (
            f"{threshold.heart_rate_bpm:.0f} bpm"
            if threshold.heart_rate_bpm is not None
            else "non validée"
        )
        print(
            f"{threshold.threshold_name.upper()} : "
            f"{speed} | {heart_rate} | "
            f"confiance {threshold.confidence_score}/100 | "
            f"{threshold.observation_count} observations"
        )


if __name__ == "__main__":
    main()
