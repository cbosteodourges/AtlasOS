from garmin_fit_sdk import Decoder, Stream

from src.integrations.garmin_workout import encode_garmin_fit, universal_workout
from tools import atlas_web_server


def sample_workout():
    return {
        "workout_id": "2026-09-15-vo2",
        "workout_date": "2026-09-15",
        "title": "VO2max 5 x 1000 m",
        "objective": "Développer la puissance aérobie.",
        "sport": "running",
        "blocks": [
            {"name": "Échauffement", "block_type": "warm_up", "duration_minutes": 20,
             "target": {"heart_rate_min_bpm": 115, "heart_rate_max_bpm": 135}},
            {"name": "1000 m", "block_type": "work", "distance_meters": 1000,
             "repetitions": 5, "recovery_minutes": 2,
             "target": {"speed_min_kmh": 12.8, "speed_max_kmh": 13.2}},
            {"name": "Retour au calme", "block_type": "cool_down", "duration_minutes": 10,
             "target": {"zone": 1}},
        ],
    }


def test_universal_workout_expands_repetitions_and_recoveries():
    result = universal_workout(sample_workout())
    assert result["schema"] == "atlas.workout.v1"
    assert len(result["steps"]) == 11
    assert [step["role"] for step in result["steps"]].count("work") == 5
    assert [step["role"] for step in result["steps"]].count("recovery") == 4


def test_fit_export_is_valid_and_keeps_targets():
    fit_data, normalized = encode_garmin_fit(sample_workout())
    decoder = Decoder(Stream.from_byte_array(fit_data))
    assert decoder.is_fit()
    assert decoder.check_integrity()
    decoder = Decoder(Stream.from_byte_array(fit_data))
    messages, errors = decoder.read()
    assert errors == []
    assert len(messages["workout_step_mesgs"]) == len(normalized["steps"])
    first = messages["workout_step_mesgs"][0]
    work = messages["workout_step_mesgs"][1]
    assert first["intensity"] == "warmup"
    assert first["duration_time"] == 1200
    assert first["custom_target_heart_rate_low"] == 215
    assert work["duration_distance"] == 1000
    assert work["target_type"] == "speed"
    assert 3.5 < work["custom_target_speed_low"] < 3.6


def test_pace_targets_are_converted_to_speed():
    workout = sample_workout()
    workout["blocks"][1]["target"] = {
        "pace_min_per_km": "4:30",
        "pace_max_per_km": "4:45",
    }
    fit_data, _ = encode_garmin_fit(workout)
    messages, errors = Decoder(Stream.from_byte_array(fit_data)).read()
    assert errors == []
    work = messages["workout_step_mesgs"][1]
    assert 3.50 < work["custom_target_speed_low"] < 3.52
    assert 3.70 < work["custom_target_speed_high"] < 3.71


def test_seconds_and_optional_ui_aliases_are_supported():
    workout = sample_workout()
    workout["blocks"] = [{
        "name": "3 x 3 minutes",
        "block_type": "interval",
        "duration_seconds": 180,
        "repetitions": 3,
        "recovery_seconds": 90,
        "instructions": "Rester relâché.",
    }]
    fit_data, normalized = encode_garmin_fit(workout)
    messages, errors = Decoder(Stream.from_byte_array(fit_data)).read()
    assert errors == []
    assert len(normalized["steps"]) == 5
    assert messages["workout_step_mesgs"][0]["intensity"] == "interval"
    assert messages["workout_step_mesgs"][0]["duration_time"] == 180
    assert messages["workout_step_mesgs"][1]["duration_time"] == 90
    assert messages["workout_step_mesgs"][0]["notes"] == "Rester relâché."


def test_reversed_ranges_are_normalized():
    workout = sample_workout()
    workout["blocks"][1]["target"] = {
        "speed_min_kmh": 14,
        "speed_max_kmh": 13,
    }
    fit_data, _ = encode_garmin_fit(workout)
    messages, errors = Decoder(Stream.from_byte_array(fit_data)).read()
    assert errors == []
    step = messages["workout_step_mesgs"][1]
    assert step["custom_target_speed_low"] < step["custom_target_speed_high"]


def test_export_uses_the_adaptation_explicitly_accepted(monkeypatch, tmp_path):
    original = sample_workout()
    adapted = sample_workout()
    adapted["title"] = "Version Atlas adaptée"
    monkeypatch.setattr(
        atlas_web_server,
        "load_authorized_training_program",
        lambda: {"weeks": [{"workouts": [original]}]},
    )
    monkeypatch.setattr(
        atlas_web_server,
        "OPTIONAL_WORKOUTS_PATH",
        tmp_path / "optional.json",
    )

    class PreparationStub:
        def __init__(self, _root):
            pass

        def latest_selection(self, _workout_id):
            return {
                "user_selection": "accept_adaptation",
                "adapted_workout": adapted,
            }

    monkeypatch.setattr(
        atlas_web_server,
        "DailyPreparationService",
        PreparationStub,
    )
    selected, version = atlas_web_server.workout_for_export(original["workout_id"])
    assert version == "adapted"
    assert selected["title"] == "Version Atlas adaptée"
