"""
The badge catalogue and the rules that earn them.

Every rule reads from one ``stats`` dict (see ``researcher_stats``) so checking all
badges for a researcher costs a handful of queries however many badges exist. A rule is
``progress(stats) -> (current, target)``; the badge is earned when ``current >= target``.
Adding a badge = adding one ``Badge(...)`` line here (no migration).
"""
from dataclasses import dataclass
from typing import Callable

from django.db.models import Count, Q

from leaderboard.models import ScoreEvent, award_statuses
from reports.models import BugReport


@dataclass(frozen=True)
class Badge:
    key: str
    name: str
    description: str
    icon: str
    progress: Callable[[dict], tuple]


def _count(stat, target):
    return lambda stats: (stats[stat], target)


BADGES = (
    Badge("first_blood", "First Blood", "Get your first report accepted.", "🩸",
          _count("accepted", 1)),
    Badge("critical_thinker", "Critical Thinker", "Get a critical-severity report accepted.", "💥",
          _count("critical", 1)),
    Badge("heavy_hitter", "Heavy Hitter", "Get 3 high or critical reports accepted.", "🔨",
          _count("high_or_critical", 3)),
    Badge("collector", "Bug Collector", "Get 10 reports accepted.", "🐞",
          _count("accepted", 10)),
    Badge("hoarder", "Bug Hoarder", "Get 25 reports accepted.", "🏆",
          _count("accepted", 25)),
    Badge("globetrotter", "Globetrotter", "Get reports accepted in 3 different programs.", "🌍",
          _count("programs", 3)),
    Badge("standout", "Standout Report", "Earn bonus points from a triager for a great report.", "⭐",
          _count("bonus_reports", 1)),
    Badge("clean_streak", "Clean Streak", "Get 5 reports accepted in a row without a rejection.", "✨",
          _count("streak", 5)),
)

BADGES_BY_KEY = {badge.key: badge for badge in BADGES}


def _accepted_streak(user):
    """Accepted reports in a row, newest first, stopping at the first rejection.
    Duplicates and still-open reports are neutral: they neither extend nor break it."""
    streak = 0
    awardable = set(award_statuses())
    statuses = (
        BugReport.objects.filter(reporter=user, status__in=[*awardable, "rejected"])
        .order_by("-created_at", "-id").values_list("status", flat=True)
    )
    for status in statuses:
        if status == "rejected":
            break
        streak += 1
    return streak


def researcher_stats(user):
    """Everything the badge rules need, in two aggregate queries plus the streak walk."""
    agg = ScoreEvent.objects.filter(researcher=user).aggregate(
        accepted=Count("id"),
        critical=Count("id", filter=Q(severity="critical")),
        high_or_critical=Count("id", filter=Q(severity__in=["high", "critical"])),
        programs=Count("program", distinct=True),
        bonus_reports=Count("id", filter=Q(report__bonus_points__gt=0)),
    )
    return {**agg, "streak": _accepted_streak(user)}
