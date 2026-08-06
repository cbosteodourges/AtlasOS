"""
ATLAS OS
Analyse détaillée d'une séance Garmin FIT privée.
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors import GarminConnector  # noqa: E402
from src.performance import (  # noqa: E402
    AthleteProfile,
    DetailedSessionAnalyzer,
    LongitudinalActivityAdapter,
    PhysiologicalReferences,
)


def parse_arguments() -> argparse.Namespace:
    """Lit les références individuelles et le fichier FIT."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyse les blocs détaillés d'une séance FIT."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Chemin du fichier FIT à analyser.",
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
            "detailed-session-analysis.json"
        ),
        help="Fichier JSON privé de sortie.",
    )
    return parser.parse_args()


def load_activity(fit_path: Path):
    """Décode et normalise uniquement le fichier demandé."""
    if not fit_path.exists():
        raise FileNotFoundError(
            f"Fichier FIT introuvable : {fit_path}"
        )

    connector = GarminConnector(
        str(fit_path.parent)
    )
    connector.connect()

    raw_activities = list(
        connector.fetch_activities()
    )
    selected = next(
        (
            activity
            for activity in raw_activities
            if activity.external_id == fit_path.stem
        ),
        None,
    )

    if selected is None:
        raise ValueError(
            f"Séance FIT non décodée : {fit_path.name}"
        )

    return connector.normalize(selected)


def write_analysis(
    analysis,
    output_path: str,
) -> Path:
    """Enregistre l'analyse dans le dossier privé."""
    destination = Path(output_path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            asdict(analysis),
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    return destination


def format_duration(seconds: float) -> str:
    """Formate une durée en minutes et secondes."""
    total_seconds = round(seconds)
    minutes, remaining_seconds = divmod(
        total_seconds,
        60,
    )
    return f"{minutes:02d}:{remaining_seconds:02d}"


def display_analysis(
    analysis,
    sample_count: int,
) -> None:
    """Affiche une synthèse lisible dans PowerShell."""
    print()
    print("ANALYSE DÉTAILLÉE DE LA SÉANCE FIT")
    print("=" * 78)
    print(f"Points détaillés : {sample_count}")
    print(f"Blocs détectés : {len(analysis.blocks)}")
    print(
        "Travail dominant : "
        f"{analysis.dominant_work_type}"
    )
    print(
        "Charge physiologique : "
        f"{analysis.physiological_load_score}/100"
    )
    print(
        "Charge biomécanique : "
        f"{analysis.biomechanical_load_score}/100"
    )
    print(
        "Confiance : "
        f"{analysis.analysis_confidence_score}/100"
    )
    print()
    print(
        "N° | Type         | Durée | Distance | "
        "Vitesse | FC moy. | Charges P/B"
    )
    print("-" * 78)

    for block in analysis.blocks:
        speed = (
            f"{block.average_speed_kmh:.1f} km/h"
            if block.average_speed_kmh is not None
            else "-"
        )
        heart_rate = (
            f"{block.average_heart_rate_bpm:.0f}"
            if block.average_heart_rate_bpm is not None
            else "-"
        )

        print(
            f"{block.block_index:>2} | "
            f"{block.block_type:<12} | "
            f"{format_duration(block.duration_seconds):>5} | "
            f"{block.distance_meters:>7.0f} m | "
            f"{speed:>11} | "
            f"{heart_rate:>7} | "
            f"{block.physiological_load_score:>2}/"
            f"{block.biomechanical_load_score:<2}"
        )

    if analysis.threshold_observations:
        print()
        print("OBSERVATIONS DE SEUILS")
        print("-" * 78)

        for observation in (
            analysis.threshold_observations
        ):
            speed = (
                f"{observation.estimated_speed_kmh:.1f} km/h"
                if observation.estimated_speed_kmh
                is not None
                else "-"
            )
            heart_rate = (
                f"{observation.estimated_heart_rate_bpm:.0f} bpm"
                if observation.estimated_heart_rate_bpm
                is not None
                else "-"
            )
            print(
                f"{observation.threshold_name.upper()} : "
                f"{speed} | {heart_rate} | "
                f"confiance "
                f"{observation.confidence_score}/100"
            )

    print()
    print("INTERPRÉTATION")
    print("-" * 78)
    for item in analysis.interpretation:
        print(f"- {item}")

    print()
    print("INFLUENCE SUR LA PLANIFICATION")
    print("-" * 78)
    for item in analysis.planning_influences:
        print(f"- {item}")


def main() -> None:
    """Lance l'analyse détaillée de la séance."""
    arguments = parse_arguments()
    normalized = load_activity(
        Path(arguments.input)
    )
    longitudinal = (
        LongitudinalActivityAdapter().adapt(
            normalized
        )
    )
    profile = AthleteProfile(
        athlete_id="local-athlete",
        declared_level="unknown",
        observed_level="unknown",
        physiological=PhysiologicalReferences(
            maximum_heart_rate_bpm=(
                arguments.max_hr
            ),
            threshold_heart_rate_bpm=(
                arguments.sv2_hr
            ),
            vma_kmh=arguments.vma,
            threshold_speed_kmh=(
                arguments.sv2_speed
            ),
        ),
    )
    analysis = DetailedSessionAnalyzer().analyze(
        longitudinal,
        profile,
    )
    destination = write_analysis(
        analysis,
        arguments.output,
    )

    display_analysis(
        analysis,
        len(longitudinal.samples),
    )
    print()
    print(f"Analyse privée enregistrée : {destination}")


if __name__ == "__main__":
    main()