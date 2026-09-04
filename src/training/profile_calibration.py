"""État de calibration du profil physiologique Atlas.

Ce module expose uniquement des repères de maturité compréhensibles par
l'utilisateur. Les règles détaillées d'estimation physiologique restent dans
le moteur de profil longitudinal.
"""

from src.training.heart_rate_speed_profile import extract_comparable_blocks


STAGE_DEFINITIONS = (
    (1, "Profil provisoire", "Renseigner les repères de départ et les disponibilités."),
    (2, "Programme sécurisé", "Démarrer immédiatement avec des intensités prudentes."),
    (3, "Calibration 2 à 4 semaines", "Enrichir le profil avec des séances FIT exploitables."),
    (4, "Actualisation hebdomadaire", "Réévaluer régulièrement les tendances confirmées."),
    (5, "Profil établi", "Relier durablement le profil, les zones et les prochaines séances."),
)


def profile_calibration_summary(executions, physiology, *, profile_exists=False,
                                program_exists=False):
    """Retourne les cinq étapes et la maturité observée du profil.

    Une séance est dite exploitable lorsqu'elle contient au moins un bloc avec
    date, durée, vitesse et fréquence cardiaque cohérentes. Les seuils de
    passage servent à l'interface d'accompagnement, pas au calcul des seuils
    physiologiques eux-mêmes.
    """

    blocks = extract_comparable_blocks(executions or [], physiology or {})
    session_ids = {block["session_id"] for block in blocks}
    weeks = {(block["date"].isocalendar().year, block["date"].isocalendar().week)
             for block in blocks}
    domain_sessions = {
        domain: len({block["session_id"] for block in blocks
                     if block["domain"] == domain})
        for domain in ("endurance", "tempo", "threshold", "vo2")
    }

    usable_sessions = len(session_ids)
    covered_weeks = len(weeks)
    covered_domains = sum(count > 0 for count in domain_sessions.values())
    readiness = {
        1: bool(profile_exists or physiology),
        2: bool((profile_exists or physiology) and program_exists),
        3: usable_sessions >= 5 and covered_weeks >= 2,
        4: usable_sessions >= 8 and covered_weeks >= 4,
        5: (
            usable_sessions >= 12
            and covered_weeks >= 4
            and covered_domains >= 3
        ),
    }

    # Les étapes restent séquentielles : Atlas n'affiche jamais une étape
    # avancée comme acquise si une fondation précédente manque.
    completed = 0
    for index in range(1, 6):
        if readiness[index] and completed == index - 1:
            completed = index
        else:
            break
    active_stage = min(5, completed + 1) if completed < 5 else 5

    stages = []
    for number, title, description in STAGE_DEFINITIONS:
        status = "completed" if number <= completed else (
            "active" if number == active_stage else "upcoming"
        )
        stages.append({
            "number": number,
            "title": title,
            "description": description,
            "status": status,
        })

    if completed >= 5:
        next_step = "Le profil est établi et continue d'être réévalué chaque semaine."
    elif completed < 2:
        next_step = "Complétez le profil de départ pour lancer un programme prudent."
    elif usable_sessions < 5:
        missing = 5 - usable_sessions
        next_step = f"Encore {missing} séance(s) FIT exploitable(s) pour consolider la calibration."
    elif covered_weeks < 4:
        next_step = "Poursuivez la calibration sur plusieurs semaines pour confirmer les tendances."
    elif usable_sessions < 12:
        next_step = f"Encore {12 - usable_sessions} séance(s) exploitable(s) pour établir le profil."
    else:
        next_step = "Diversifiez les filières observées pour établir le profil complet."

    return {
        "schema_version": "profile_calibration_v1",
        "active_stage": active_stage,
        "completed_stage_count": completed,
        "usable_session_count": usable_sessions,
        "covered_week_count": covered_weeks,
        "domain_session_counts": domain_sessions,
        "stages": stages,
        "next_step": next_step,
    }
