from django.db import transaction

from .definitions import BADGES, researcher_stats
from .models import UserBadge


def evaluate(user):
    """
    Award every badge the researcher now qualifies for. Idempotent and safe to call as
    often as you like. Returns the list of newly earned ``UserBadge`` rows.
    """
    from store import services as store  # lazy: the store reads badges too

    have = set(UserBadge.objects.filter(user=user).values_list("key", flat=True))
    new = []
    if len(have) < len(BADGES):
        stats = researcher_stats(user)
        with transaction.atomic():
            for badge in BADGES:
                if badge.key in have:
                    continue
                current, target = badge.progress(stats)
                if current >= target:
                    row, created = UserBadge.objects.get_or_create(user=user, key=badge.key)
                    if created:
                        new.append(row)
    # Free items that belong to earned badges (also for badges earned before the item existed).
    store.grant_badge_rewards(user)
    return new


def overview(user):
    """Every badge with whether ``user`` has it, when, and progress toward the rest."""
    from store.models import Item, UserItem

    earned = {row.key: row for row in UserBadge.objects.filter(user=user)}
    stats = researcher_stats(user)
    owned = set(UserItem.objects.filter(user=user).values_list("item_id", flat=True))
    rewards = {}
    for item in Item.objects.filter(is_active=True).exclude(unlock_badge=""):
        rewards.setdefault(item.unlock_badge, []).append({
            "slug": item.slug, "name": item.name, "art": item.art, "slot": item.slot,
            "rarity": item.rarity, "price": item.price, "owned": item.pk in owned,
        })
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
            "rewards": rewards.get(badge.key, []),
        })
    return out

