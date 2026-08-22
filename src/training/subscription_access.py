"""Contrôle d'accès aux programmes Atlas selon l'abonnement."""

from copy import deepcopy
from datetime import date, timedelta


FULL_ACCESS_TIERS = {"annual", "founder_admin"}


def normalize_tier(value):
    """Retourne un niveau d'accès connu, mensuel par défaut."""

    tier = str(value or "").strip().lower()
    return tier if tier in {
        "monthly", "annual", "founder_admin", "trial", "expired"
    } else "monthly"


def _day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def filter_program_for_subscription(program, tier, today=None):
    """Ne transmet que les semaines autorisées et résume les semaines bloquées."""

    current_day = today or date.today()
    normalized = normalize_tier(tier)
    result = deepcopy(program or {})
    weeks = sorted(
        result.get("weeks") or [],
        key=lambda item: (
            _day(item.get("start_date")) or date.max,
            int(item.get("week_number") or 0),
        ),
    )

    if normalized in FULL_ACCESS_TIERS:
        result["weeks"] = weeks
        result["locked_weeks"] = []
        result["access_control"] = {
            "tier": normalized,
            "full_access": True,
            "rolling_weeks": None,
            "visible_week_count": len(weeks),
            "locked_week_count": 0,
            "can_print_full_program": True,
        }
        return result

    first_future_index = next(
        (
            index
            for index, week in enumerate(weeks)
            if (_day(week.get("end_date")) or _day(week.get("start_date"))
                or date.max) >= current_day
        ),
        len(weeks),
    )
    rolling_weeks = 2 if normalized == "trial" else 4
    future_limit = (
        first_future_index
        if normalized == "expired"
        else min(len(weeks), first_future_index + rolling_weeks)
    )
    visible = weeks[:future_limit]
    locked = weeks[future_limit:]

    result["weeks"] = visible
    result["locked_weeks"] = [
        {
            "week_number": week.get("week_number"),
            "start_date": week.get("start_date"),
            "end_date": week.get("end_date"),
            "phase": week.get("phase"),
            "unlock_date": (
                (_day(week.get("start_date")) - timedelta(days=21)).isoformat()
                if normalized == "monthly" and _day(week.get("start_date"))
                else None
            ),
        }
        for week in locked
    ]
    result["access_control"] = {
        "tier": normalized,
        "full_access": False,
        "rolling_weeks": 0 if normalized == "expired" else rolling_weeks,
        "visible_week_count": len(visible),
        "locked_week_count": len(locked),
        "can_print_full_program": False,
    }
    return result
