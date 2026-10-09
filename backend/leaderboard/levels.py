"""
Researcher levels.

A level is a pure function of *lifetime* points earned (the sum of the ScoreEvent
ledger), so nothing is stored: it can never drift from the points behind it, and
changing the table below re-levels everyone instantly. Spending points in the
wallet never changes a level. Revoked points (a report later rejected) can.

Override the table with ``settings.LEADERBOARD_LEVELS``: a list of
``(min_points, title)`` pairs. It must start at 0 points and be strictly increasing.
"""
from django.conf import settings
from django.db.models import Sum

from .models import ScoreEvent

DEFAULT_LEVELS = (
    (0, "Bug Sprout"),
    (50, "Bug Hatchling"),
    (150, "Bug Scout"),
    (350, "Bug Hunter"),
    (700, "Bug Wrangler"),
    (1200, "Bug Slayer"),
    (2000, "Bug Whisperer"),
    (3500, "Bug Legend"),
)


def level_table():
    """The configured levels as a validated tuple of ``(min_points, title)``."""
    table = tuple(getattr(settings, "LEADERBOARD_LEVELS", DEFAULT_LEVELS))
    if not table or table[0][0] != 0:
        raise ValueError("LEADERBOARD_LEVELS must start with a level at 0 points")
    if any(b[0] <= a[0] for a, b in zip(table, table[1:])):
        raise ValueError("LEADERBOARD_LEVELS must be strictly increasing in points")
    return table


def level_for(points):
    """
    Where ``points`` lifetime points put a researcher:

        level (1-based), title, min_points, next_title / next_at (None at the top),
        points_to_next, progress (0.0-1.0 through the current level; 1.0 at the top)
    """
    points = max(int(points or 0), 0)
    table = level_table()
    index = 0
    for i, (minimum, _) in enumerate(table):
        if points >= minimum:
            index = i
    minimum, title = table[index]
    nxt = table[index + 1] if index + 1 < len(table) else None
    if nxt is None:
        progress, to_next = 1.0, 0
    else:
        progress = (points - minimum) / (nxt[0] - minimum)
        to_next = nxt[0] - points
    return {
        "level": index + 1,
        "title": title,
        "min_points": minimum,
        "next_title": nxt[1] if nxt else None,
        "next_at": nxt[0] if nxt else None,
        "points_to_next": to_next,
        "progress": round(progress, 4),
    }


def lifetime_points(user_ids):
    """``{user_id: lifetime points}`` for many researchers in one query."""
    rows = (
        ScoreEvent.objects.filter(researcher_id__in=list(user_ids))
        .values("researcher_id").annotate(total=Sum("points"))
    )
    return {row["researcher_id"]: row["total"] or 0 for row in rows}


def level_info_for_users(user_ids):
    """``{user_id: level_for(...)}``; researchers with no points are level 1."""
    points = lifetime_points(user_ids)
    return {uid: level_for(points.get(uid, 0)) for uid in user_ids}


def levels_overview():
    """The whole ladder, for the 'what are the levels?' UI."""
    return [
        {"level": i + 1, "title": title, "min_points": minimum}
        for i, (minimum, title) in enumerate(level_table())
    ]
