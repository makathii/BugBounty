from django.db import transaction

from .definitions import BADGES, researcher_stats
from .models import UserBadge


def evaluate(user):
    """
    Award every badge the researcher now qualifies for. Idempotent and safe to call as
    often as you like. Returns the list of newly earned ``UserBadge`` rows.
    """
    have = set(UserBadge.objects.filter(user=user).values_list("key", flat=True))
    if len(have) == len(BADGES):
        return []
    stats = researcher_stats(user)
    new = []
    with transaction.atomic():
        for badge in BADGES:
            if badge.key in have:
                continue
            current, target = badge.progress(stats)
            if current >= target:
                row, created = UserBadge.objects.get_or_create(user=user, key=badge.key)
                if created:
                    new.append(row)
    return new


def overview(user):
    """Every badge with whether ``user`` has it, when, and progress toward the rest."""
    earned = {row.key: row for row in UserBadge.objects.filter(user=user)}
    stats = researcher_stats(user)
    out = []
    for badge in BADGES:
        current, target = badge.progress(stats)
        row = earned.get(badge.key)
        out.append({
            "key": badge.key,
            "name": badge.name,
            "description": badge.description,
            "icon": badge.icon,
            "earned": row is not None,
            "awarded_at": row.awarded_at if row else None,
            "progress": {"current": min(current, target), "target": target},
        })
    return out

