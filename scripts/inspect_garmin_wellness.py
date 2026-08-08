"""
ATLAS OS
Inspection ciblée des données quotidiennes Garmin.
"""

from pathlib import Path
from pprint import pprint

from garmin_fit_sdk import Decoder, Stream


INPUT_DIRECTORY = Path(
    "atlas-data/private/wellness-inspection/2026-08-05"
)

TARGET_GROUPS = {
    "hrv_status_summary_mesgs",
    "sleep_assessment_mesgs",
    "monitoring_hr_data_mesgs",
    "sleep_level_mesgs",
    "521",
    "382",
    "273",
}


def main() -> None:
    """Affiche les valeurs utiles d'une journée Garmin."""
    for fit_path in sorted(INPUT_DIRECTORY.glob("*.fit")):
        stream = Stream.from_file(str(fit_path))
        decoder = Decoder(stream)
        messages, errors = decoder.read()

        selected_groups = {
            str(name): records
            for name, records in messages.items()
            if str(name) in TARGET_GROUPS
        }

        if not selected_groups:
            continue

        print()
        print("=" * 72)
        print(f"FICHIER : {fit_path.name}")
        print(f"ERREURS : {len(errors)}")

        for name, records in selected_groups.items():
            print()
            print(f"{name} : {len(records)} message(s)")

            if name == "sleep_level_mesgs":
                pprint(records)
            else:
                for record in records:
                    pprint(record)


if __name__ == "__main__":
    main()