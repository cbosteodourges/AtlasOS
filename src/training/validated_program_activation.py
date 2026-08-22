"""Activation du programme 3+1 validé jusqu'à l'échéance."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any


START_DATE = date(2026, 8, 22)
CYCLE_START_DATE = date(2026, 8, 24)
EVENT_DATE = date(2026, 10, 25)
SPECIFIC_CAP_MINUTES = 60


def _target(snapshot: dict[str, Any], kind: str) -> dict[str, Any]:
    vma = float(snapshot.get("vma_training_reference_kmh") or snapshot.get("vma_kmh") or 14.0)
    maximum_hr = int(snapshot.get("maximum_heart_rate_bpm") or 170)
    sv1 = snapshot.get("sv1") or {}
    sv2 = snapshot.get("sv2") or {}
    sv1_speed = float(sv1.get("speed_kmh") or vma * .75)
    sv1_hr = int(sv1.get("heart_rate_bpm") or maximum_hr * .78)
    sv2_speed = float(sv2.get("speed_kmh") or vma * .90)
    sv2_hr = int(sv2.get("heart_rate_bpm") or maximum_hr * .90)
    if kind == "vo2":
        return {"zone": 4, "speed_min_kmh": round(vma * .95, 1), "speed_max_kmh": round(vma, 1),
                "heart_rate_min_bpm": round(maximum_hr * .88), "heart_rate_max_bpm": round(maximum_hr * .95),
                "rpe_0_10": 7, "intensity_pattern": "interval"}
    if kind == "subthreshold":
        return {"zone": 3, "speed_min_kmh": round(sv2_speed * .92, 1), "speed_max_kmh": round(sv2_speed * .97, 1),
                "heart_rate_min_bpm": max(sv1_hr + 2, sv2_hr - 10), "heart_rate_max_bpm": sv2_hr - 3,
                "rpe_0_10": 5.5, "intensity_pattern": "interval"}
    if kind == "sv2":
        return {"zone": 3, "speed_min_kmh": round(sv2_speed * .97, 1), "speed_max_kmh": round(sv2_speed, 1),
                "heart_rate_min_bpm": max(sv1_hr + 3, sv2_hr - 7), "heart_rate_max_bpm": sv2_hr,
                "rpe_0_10": 6, "intensity_pattern": "interval"}
    if kind == "goal":
        return {"zone": 3, "speed_min_kmh": 11.4, "speed_max_kmh": 11.8,
                "heart_rate_min_bpm": sv1_hr, "heart_rate_max_bpm": max(sv1_hr, sv2_hr - 4),
                "rpe_0_10": 5.5, "intensity_pattern": "constant"}
    if kind == "recovery":
        return {"zone": 1, "speed_min_kmh": round(vma * .55, 1), "speed_max_kmh": round(vma * .65, 1),
                "heart_rate_min_bpm": round(maximum_hr * .62), "heart_rate_max_bpm": min(125, sv1_hr - 5),
                "rpe_0_10": 2, "intensity_pattern": "constant"}
    return {"zone": 2, "speed_min_kmh": round(vma * .65, 1), "speed_max_kmh": round(sv1_speed, 1),
            "heart_rate_min_bpm": round(maximum_hr * .68), "heart_rate_max_bpm": min(135, sv1_hr),
            "rpe_0_10": 3, "intensity_pattern": "constant"}


def _block(name: str, block_type: str, *, duration: float | None = None,
           distance: int | None = None, repetitions: int = 1,
           recovery: float | None = None, target: dict[str, Any] | None = None,
           instructions: str = "") -> dict[str, Any]:
    return {"name": name, "block_type": block_type, "repetitions": repetitions,
            "duration_minutes": duration, "distance_meters": distance,
            "recovery_minutes": recovery, "target": target or {},
            "instructions": instructions}


def _workout(day: date, key: str, workout_type: str, title: str, objective: str,
             duration: int, blocks: list[dict[str, Any]], *, priority: str = "key",
             sport: str = "running", movable: bool = True,
             notes: list[str] | None = None) -> dict[str, Any]:
    quality = priority == "key"
    return {
        "workout_id": f"{day.isoformat()}-validated-3plus1-{key}",
        "workout_date": day.isoformat(), "workout_type": workout_type,
        "title": title, "objective": objective, "blocks": blocks,
        "sport": sport, "priority": priority,
        "planned_duration_minutes": duration, "planned_distance_km": None,
        "expected_response": {
            "physiological_load_0_100": 72 if quality else 38,
            "biomechanical_load_0_100": 58 if quality else 30,
            "recovery_min_hours": 36 if quality else 18,
            "recovery_max_hours": 48 if quality else 30,
            "sensitive_structures": ["mollets", "tendons d'Achille"] if quality else [],
        },
        "movable": movable, "maximum_shift_days": 1 if quality else 2,
        "replacement_types": ["endurance_z2"] if sport == "running" else [],
        "coach_notes": notes or [],
    }


def _easy(day: date, minutes: int, snapshot: dict[str, Any], key: str = "easy") -> dict[str, Any]:
    return _workout(day, key, "endurance_z2", "Endurance fondamentale Z2",
                    "Développer l'endurance et favoriser la récupération.", minutes,
                    [_block("Course continue Z2", "continuous", duration=minutes,
                            target=_target(snapshot, "z2"))], priority="support")


def _quality(day: date, key: str, workout_type: str, title: str, objective: str,
             duration: int, work_blocks: list[dict[str, Any]],
             snapshot: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    blocks = [_block("Échauffement progressif", "warm_up", duration=15,
                     target=_target(snapshot, "recovery"),
                     instructions="Terminer par trois accélérations progressives.")]
    blocks.extend(work_blocks)
    blocks.append(_block("Retour au calme", "cool_down", duration=10,
                         target=_target(snapshot, "recovery")))
    common = [
        "Commencer par la borne basse ; les répétitions supplémentaires restent facultatives.",
        "Terminer avec la sensation de pouvoir encore effectuer une répétition propre.",
        "Arrêter si douleur, dégradation technique ou RPE supérieur à 7/10.",
        "Les options hautes sont interdépendantes : 60 min spécifiques maximum par semaine.",
    ]
    return _workout(day, key, workout_type, title, objective, duration, blocks,
                    notes=notes + common)


def _strength(day: date, minutes: int = 20) -> dict[str, Any]:
    return _workout(day, "strength", "strength", "Renforcement fonctionnel course",
                    "Entretenir la force sans fatigue résiduelle.", minutes,
                    [_block("Circuit contrôlé", "strength", duration=minutes,
                            instructions="Chaîne postérieure, mollets, gainage et contrôle unipodal.")],
                    priority="support", sport="strength")


def _mobility(day: date, minutes: int = 15) -> dict[str, Any]:
    return _workout(day, "mobility", "mobility", "Mobilité et récupération",
                    "Restaurer la mobilité et diminuer la tension musculaire.", minutes,
                    [_block("Mobilité globale", "mobility", duration=minutes,
                            instructions="Mobilité douce, sans recherche d'amplitude forcée.")],
                    priority="support", sport="mobility")


def _cycling(day: date, minutes: int = 60) -> dict[str, Any]:
    return _workout(day, "cycling", "cycling", "Vélo de récupération facultatif",
                    "Ajouter une charge aérobie sans contrainte mécanique importante.", minutes,
                    [_block("Vélo facile", "continuous", duration=minutes,
                            target={"zone": 1, "rpe_0_10": 2.5},
                            instructions="Faible résistance, aucune accélération finale.")],
                    priority="optional", sport="cycling")


def _vo2_distance(day: date, distance: int, low: int, high: int,
                  snapshot: dict[str, Any], duration: int) -> dict[str, Any]:
    return _quality(day, "vo2", "vma_short",
        f"VO₂max contrôlée · {low} à {high} × {distance} m",
        "Développer la puissance aérobie sans épuisement.", duration,
        [_block(f"{low} à {high} × {distance} m", "work", distance=distance,
                repetitions=low, recovery=1.5, target=_target(snapshot, "vo2"),
                instructions=f"{low} répétitions prévues ; jusqu'à {high} seulement si tous les critères restent verts.")],
        snapshot, [f"Fourchette autorégulée : {low} à {high} répétitions."])


def _vo2_time(day: date, low: int, high: int, seconds: int,
              snapshot: dict[str, Any], duration: int) -> dict[str, Any]:
    minutes = seconds / 60
    return _quality(day, "vo2-time", "vma_long",
        f"Temps de soutien VO₂max · {low} à {high} × {seconds // 60 if seconds % 60 == 0 else '1 min 30'}",
        "Développer le temps de soutien à VO₂max avec une exécution régulière.", duration,
        [_block(f"{low} à {high} répétitions", "work", duration=minutes,
                repetitions=low, recovery=2, target=_target(snapshot, "vo2"),
                instructions=f"Commencer par {low}; plafond {high} si la dernière fraction reste propre.")],
        snapshot, [f"Volume possible : {low * minutes:g} à {high * minutes:g} min."])


def _vo2_pyramid(day: date, snapshot: dict[str, Any], duration: int) -> dict[str, Any]:
    target = _target(snapshot, "vo2")
    return _quality(day, "vo2-pyramid", "triangular_vo2",
        "VO₂max pyramidal · 2 × 3 min + 2 × 2 min + 1 à 2 × 1 min 30",
        "Varier le temps de soutien tout en conservant la qualité gestuelle.", duration,
        [_block("2 × 3 min", "work", duration=3, repetitions=2, recovery=1.5, target=target),
         _block("2 × 2 min", "work", duration=2, repetitions=2, recovery=1.5, target=target),
         _block("1 à 2 × 1 min 30", "work", duration=1.5, repetitions=1, recovery=1.5,
                target=target, instructions="La seconde répétition est facultative.")],
        snapshot, ["Noyau de 11 min 30 ; maximum 13 min."])


def _threshold_1000(day: date, low: int, high: int,
                    snapshot: dict[str, Any], duration: int) -> dict[str, Any]:
    return _quality(day, "sv2-1000", "threshold_sv2",
        f"SV2 contrôlé · {low} à {high} × 1000 m",
        "Élever le seuil tout en maintenant une marge de récupération.", duration,
        [_block(f"{low} à {high} × 1000 m", "work", distance=1000,
                repetitions=low, recovery=1.75, target=_target(snapshot, "sv2"),
                instructions=f"La répétition {high} est facultative selon sensations et enveloppe hebdomadaire.")],
        snapshot, [f"Fourchette autorégulée : {low} à {high} répétitions."])


def _threshold_desc(day: date, snapshot: dict[str, Any], duration: int) -> dict[str, Any]:
    target = _target(snapshot, "sv2")
    return _quality(day, "sv2-desc", "threshold_sv2",
        "SV2 descendant · 2000 m + 1600 m + 1200 m facultatif",
        "Accumuler du temps au SV2 avec des fractions progressivement plus courtes.", duration,
        [_block("2000 m", "work", distance=2000, recovery=2, target=target),
         _block("1600 m", "work", distance=1600, recovery=1.75, target=target),
         _block("1200 m facultatifs", "work", distance=1200, target=target,
                instructions="Effectuer uniquement si la séance reste contrôlée.")],
        snapshot, ["Deux fractions constituent le noyau ; la troisième reste facultative."])


def _hybrid(day: date, reps: int, work_minutes: int, total_minutes: int,
            snapshot: dict[str, Any], key: str) -> dict[str, Any]:
    work = reps * work_minutes
    easy_minutes = max(20, total_minutes - work - (reps - 1) * 2 - 25)
    return _quality(day, key, "long_run",
        f"Sortie longue hybride · {reps} × {work_minutes} min sous SV2",
        "Développer la résistance à la fatigue en restant sous le seuil.", total_minutes,
        [_block("Endurance avant les blocs", "continuous", duration=easy_minutes,
                target=_target(snapshot, "z2")),
         _block(f"{reps} × {work_minutes} min sous SV2", "work",
                duration=work_minutes, repetitions=reps, recovery=2,
                target=_target(snapshot, "subthreshold"),
                instructions="RPE 5–6/10 ; rester sous SV2 et ne jamais transformer le dernier bloc en test.")],
        snapshot, [f"Volume spécifique : {work} min. Durée totale : {total_minutes} min."])


def _week(number: int, start: date, phase: str, objective: str,
          workouts: list[dict[str, Any]], recovery: bool = False) -> dict[str, Any]:
    return {"week_number": number, "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=6)).isoformat(), "phase": phase,
            "objective": objective, "workouts": sorted(workouts, key=lambda x: x["workout_date"]),
            "target_running_distance_km": None,
            "target_duration_minutes": sum(int(x.get("planned_duration_minutes") or 0) for x in workouts),
            "is_recovery_week": recovery,
            "coach_notes": ["Programme Norwegian Singles 3+1 validé par l'utilisateur.",
                            "Autorégulation obligatoire et adaptation quotidienne par Atlas Wellness."]}


def build_validated_weeks(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    weeks: list[dict[str, Any]] = []
    starts = [CYCLE_START_DATE + timedelta(weeks=i) for i in range(9)]

    def build_week(index: int, workouts: list[dict[str, Any]], phase: str, objective: str,
                   recovery: bool = False) -> None:
        weeks.append(_week(index + 2, starts[index], phase, objective, workouts, recovery))

    introduction = _week(
        1,
        START_DATE,
        "development",
        "Introduction sous-seuil avant le premier cycle complet",
        [
            _hybrid(START_DATE, 3, 6, 70, snapshot, "intro-hybrid-3x6"),
            _cycling(START_DATE + timedelta(days=1), 45),
        ],
    )
    introduction["end_date"] = (START_DATE + timedelta(days=1)).isoformat()
    weeks.append(introduction)

    for i, (vo2, threshold, hybrid) in enumerate([
        (lambda d: _vo2_distance(d, 400, 6, 8, snapshot, 48),
         lambda d: _threshold_1000(d, 3, 4, snapshot, 50),
         lambda d: _hybrid(d, 3, 8, 80, snapshot, "hybrid-3x8")),
        (lambda d: _vo2_pyramid(d, snapshot, 50),
         lambda d: _threshold_desc(d, snapshot, 54),
         lambda d: _hybrid(d, 5, 5, 85, snapshot, "hybrid-5x5")),
        (lambda d: _vo2_time(d, 4, 6, 180, snapshot, 54),
         lambda d: _threshold_1000(d, 4, 5, snapshot, 55),
         lambda d: _hybrid(d, 8, 3, 90, snapshot, "hybrid-8x3")),
    ]):
        start = starts[i]
        build_week(i, [_easy(start, 45, snapshot), vo2(start + timedelta(days=1)),
                       _strength(start + timedelta(days=2)), threshold(start + timedelta(days=3)),
                       _mobility(start + timedelta(days=4)), hybrid(start + timedelta(days=5)),
                       _cycling(start + timedelta(days=6), 60)],
                   "development", f"Cycle 1 · semaine de charge {i + 1}")

    start = starts[3]
    build_week(3, [_easy(start, 35, snapshot),
                   _easy(start + timedelta(days=1), 40, snapshot, "hill-microdose"),
                   _strength(start + timedelta(days=2), 18),
                   _easy(start + timedelta(days=3), 35, snapshot, "easy-2"),
                   _easy(start + timedelta(days=5), 40, snapshot, "strides"),
                   _cycling(start + timedelta(days=6), 50)],
               "recovery", "Consolidation · endurance et microdoses", True)
    weeks[-1]["workouts"][1]["title"] = "Endurance + 6 à 8 × 12 s en côte"
    weeks[-1]["workouts"][1]["coach_notes"].append("Récupération complète 2 min 30 ; aucune fatigue résiduelle.")
    weeks[-1]["workouts"][-2]["title"] = "Endurance + 6 à 8 × 20 s relâchées"
    weeks[-1]["workouts"][-2]["coach_notes"].append("85–92 %, récupération complète 2 min.")

    second = [
        (lambda d: _vo2_distance(d, 400, 6, 8, snapshot, 50),
         lambda d: _threshold_1000(d, 3, 4, snapshot, 52),
         lambda d: _hybrid(d, 3, 10, 95, snapshot, "hybrid-3x10")),
        (lambda d: _vo2_time(d, 4, 6, 180, snapshot, 54),
         lambda d: _threshold_desc(d, snapshot, 55),
         lambda d: _hybrid(d, 5, 6, 100, snapshot, "hybrid-5x6")),
        (lambda d: _vo2_pyramid(d, snapshot, 50),
         lambda d: _threshold_1000(d, 4, 5, snapshot, 55),
         lambda d: _hybrid(d, 8, 3, 95, snapshot, "hybrid-8x3-peak")),
    ]
    for offset, (vo2, threshold, hybrid) in enumerate(second, start=4):
        start = starts[offset]
        build_week(offset, [_easy(start, 45, snapshot), vo2(start + timedelta(days=1)),
                            _strength(start + timedelta(days=2)), threshold(start + timedelta(days=3)),
                            _mobility(start + timedelta(days=4)), hybrid(start + timedelta(days=5)),
                            _cycling(start + timedelta(days=6), 50)],
                   "specific", f"Cycle 2 · développement spécifique semi {offset - 3}")

    start = starts[7]
    build_week(7, [_easy(start, 40, snapshot),
                   _vo2_distance(start + timedelta(days=1), 400, 5, 6, snapshot, 43),
                   _mobility(start + timedelta(days=2), 15),
                   _threshold_1000(start + timedelta(days=3), 3, 3, snapshot, 45),
                   _hybrid(start + timedelta(days=5), 3, 5, 70, snapshot, "taper-hybrid")],
               "taper", "Affûtage · réduire la charge en conservant la vitesse")

    start = starts[8]
    race = _workout(EVENT_DATE, "race", "race_specific",
                    "Semi-marathon de Lille · objectif 1 h 49",
                    "Réaliser l'objectif principal avec une allure régulière.", 109,
                    [_block("Semi-marathon", "continuous", distance=21100,
                            target=_target(snapshot, "goal"),
                            instructions="Départ contrôlé, stabilisation puis accélération seulement après le 16e km.")],
                    movable=False, notes=["Épreuve cible du programme validé."])
    build_week(8, [_easy(start, 35, snapshot),
                   _vo2_time(start + timedelta(days=1), 5, 6, 60, snapshot, 38),
                   _mobility(start + timedelta(days=2), 12),
                   _easy(start + timedelta(days=3), 30, snapshot, "race-easy"),
                   race], "race_week", "Semaine de course · fraîcheur prioritaire")
    weeks[-1]["workouts"][-2]["title"] = "Endurance facile + 4 lignes droites"

    return weeks


def activate_program(active: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(active)
    goal = result.get("goal") or {}
    if str(goal.get("event_date"))[:10] != EVENT_DATE.isoformat():
        raise ValueError("L'échéance active n'est pas le 25 octobre 2026.")
    snapshot = result.get("athlete_snapshot") or {}
    weeks = build_validated_weeks(snapshot)
    result["start_date"] = START_DATE.isoformat()
    result["end_date"] = EVENT_DATE.isoformat()
    result["weeks"] = weeks
    result["duration_weeks"] = len(weeks)
    result["total_workouts"] = sum(len(week["workouts"]) for week in weeks)
    result["total_running_workouts"] = sum(
        workout.get("sport") == "running"
        for week in weeks for workout in week["workouts"]
    )
    result["explanation"] = (
        "Programme Norwegian Singles 3+1 validé dès le 22 août : introduction sous-seuil, deux cycles variables, "
        "consolidation, affûtage et semaine de course. "
        "Bornes autorégulées et plafond hebdomadaire de 60 min spécifiques."
    )
    result["warnings"] = list(dict.fromkeys(list(result.get("warnings") or []) + [
        "Les bornes hautes ne constituent jamais une obligation.",
        "Douleur, technique dégradée ou Wellness rouge : remplacement par endurance facile.",
        "Le plafond de 60 minutes spécifiques par semaine reste absolu.",
    ]))
    result["validated_three_plus_one"] = {
        "activated": True, "validated_on": date.today().isoformat(),
        "start_date": START_DATE.isoformat(), "event_date": EVENT_DATE.isoformat(),
        "specific_cap_minutes": SPECIFIC_CAP_MINUTES,
    }
    return result
