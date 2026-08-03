"""
ATLAS OS
Liste les compétitions et performances Garmin probables.
"""

import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.connectors.garmin_history import (  # noqa: E402
    GarminHistoryConnector,
)
from src.performance import (  # noqa: E402
    LongitudinalActivity,
    LongitudinalActivityAdapter,
)


def load_running_activities() -> List[
    LongitudinalActivity
]:
    """Charge les activités de course Garmin."""
    connector = GarminHistoryConnector(
        "atlas-data/garmin/Activities.csv"
    )
    connector.connect()

    adapter = LongitudinalActivityAdapter()
    running: List[LongitudinalActivity] = []

    for raw_activity in connector.fetch_activities():
        normalized = connector.normalize(
            raw_activity
        )
        activity = adapter.adapt(normalized)

        if (
            "running" in activity.activity_type
            or activity.activity_type
            in {"ultrafond", "ultra_running"}
        ):
            running.append(activity)

    return running


def format_pace(
    activity: LongitudinalActivity,
) -> str:
    """Formate l'allure moyenne."""
    pace = activity.pace_seconds_per_km

    if pace is None:
        return "—"

    seconds = round(pace)
    return (
        f"{seconds // 60}'"
        f"{seconds % 60:02d}/km"
    )


def display_activity(
    activity: LongitudinalActivity,
) -> None:
    """Affiche une activité candidate."""
    heart_rate = (
        f"{activity.average_heart_rate_bpm:.0f} bpm"
        if activity.average_heart_rate_bpm
        is not None
        else "FC inconnue"
    )

    print(
        f"{activity.start_time.date()} | "
        f"{activity.title or 'Sans titre'} | "
        f"{activity.distance_km:.2f} km | "
        f"{format_pace(activity)} | "
        f"{heart_rate}"
    )


def main() -> None:
    """Affiche les candidats à confirmer."""
    running = load_running_activities()

    comparable = [
        activity
        for activity in running
        if (
            activity.distance_km >= 4.5
            and activity.pace_seconds_per_km
            is not None
        )
    ]

    fastest = sorted(
        comparable,
        key=lambda activity: (
            activity.pace_seconds_per_km
            or float("inf")
        ),
    )[:30]

    long_events = sorted(
        [
            activity
            for activity in running
            if activity.distance_km >= 18
        ],
        key=lambda activity: activity.start_time,
    )

    print("=" * 88)
    print("ATLAS OS - 30 PERFORMANCES RAPIDES À EXAMINER")
    print("=" * 88)

    for activity in fastest:
        display_activity(activity)

    print()
    print("=" * 88)
    print("ACTIVITÉS DE 18 KM OU PLUS")
    print("=" * 88)

    for activity in long_events:
        display_activity(activity)


if __name__ == "__main__":
    main()