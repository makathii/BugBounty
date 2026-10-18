"""
Store logic: buying, owning and wearing items. The API and admin go through here.

Buying is one database transaction: the points leave the wallet and the item lands in the
inventory together, or neither happens.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from leaderboard.levels import level_for
from wallet import services as wallet

from badges.definitions import BADGES_BY_KEY
from badges.models import UserBadge

from .models import EquippedItem, Item, UserItem


class StoreError(Exception):
    """Base class: ``code`` is a stable machine-readable reason for the API."""
    code = "store_error"


class ItemUnavailable(StoreError):
    code = "item_unavailable"


class AlreadyOwned(StoreError):
    code = "already_owned"


class LevelTooLow(StoreError):
    code = "level_too_low"

    def __init__(self, required, current):
        self.required, self.current = required, current
        super().__init__(f"Requires level {required} (you are level {current}).")


class BadgeRequired(StoreError):
    code = "badge_required"

    def __init__(self, badge_key, badge_name):
        self.badge_key, self.badge_name = badge_key, badge_name
        super().__init__(f"Earn the {badge_name} badge to unlock this.")


class NotOwned(StoreError):
    code = "not_owned"


InsufficientPoints = wallet.InsufficientPoints


def purchase(user, item):
    """
    Buy ``item`` for ``user``. Returns the new ``UserItem``.

    Raises ``ItemUnavailable`` (retired), ``AlreadyOwned``, ``LevelTooLow`` or
    ``InsufficientPoints`` (nothing is charged in any of those cases).
    """
    with transaction.atomic():
        # Lock the user first: two simultaneous purchases serialise here, so the
        # ownership and balance checks below cannot both pass for the same wallet.
        get_user_model().objects.select_for_update().get(pk=user.pk)

        item = Item.objects.get(pk=item.pk)  # fresh price/active flag, not a stale object
        if not item.is_active:
            raise ItemUnavailable("This item is no longer for sale.")
        if UserItem.objects.filter(user=user, item=item).exists():
            raise AlreadyOwned("You already own this item.")
        level = level_for(wallet.lifetime_earned(user))["level"]
        if level < item.min_level:
            raise LevelTooLow(item.min_level, level)
        if item.unlock_badge and not UserBadge.objects.filter(user=user, key=item.unlock_badge).exists():
            badge = BADGES_BY_KEY.get(item.unlock_badge)
            raise BadgeRequired(item.unlock_badge, badge.name if badge else item.unlock_badge)

        tx = None
        if item.price > 0:
            tx = wallet.spend(user, item.price, f"Bought {item.name}", reference=f"item:{item.pk}")
        return UserItem.objects.create(user=user, item=item, price_paid=item.price, transaction=tx)


def grant_badge_rewards(user):
    """
    Give ``user`` every free, badge-gated item for the badges they have earned and don't yet own.
    Idempotent, and it also catches up researchers who earned a badge before the item existed.
    Returns the new ``UserItem`` rows.
    """
    earned = list(UserBadge.objects.filter(user=user).values_list("key", flat=True))
    if not earned:
        return []
    owned = UserItem.objects.filter(user=user).values_list("item_id", flat=True)
    rewards = Item.objects.filter(is_active=True, price=0, unlock_badge__in=earned).exclude(pk__in=owned)
    granted = []
    for item in rewards:
        row, created = UserItem.objects.get_or_create(user=user, item=item, defaults={"price_paid": 0})
        if created:
            granted.append(row)
    return granted


def refund(user_item, reason=None):
    """Take an item back and return what was paid (staff tool). Also unequips it."""
    with transaction.atomic():
        user_item = UserItem.objects.select_for_update(of=("self",)).select_related("item", "transaction").get(
            pk=user_item.pk
        )
        if user_item.transaction_id:
            wallet.refund(user_item.transaction, reason or f"Refund: {user_item.item.name}")
        user_item.delete()  # cascades to EquippedItem


def equip(user, item):
    """Wear an owned item, replacing whatever is in its slot."""
    with transaction.atomic():
        try:
            owned = UserItem.objects.select_related("item").get(user=user, item=item)
        except UserItem.DoesNotExist:
            raise NotOwned("You don't own this item.") from None
        EquippedItem.objects.filter(user=user, slot=owned.item.slot).delete()
        return EquippedItem.objects.create(user=user, slot=owned.item.slot, user_item=owned)


def unequip(user, item):
    """Take an owned item off. Returns True if it was being worn."""
    deleted, _ = EquippedItem.objects.filter(user=user, user_item__item=item).delete()
    return deleted > 0


def loadouts_for(user_ids):
    """``{user_id: {slot: {slug, name, slot, rarity, art, image_url}}}`` in one query, for lists."""
    out = {}
    rows = EquippedItem.objects.filter(user_id__in=list(user_ids)).select_related("user_item__item")
    for row in rows:
        item = row.user_item.item
        out.setdefault(row.user_id, {})[row.slot] = {
            "slug": item.slug, "name": item.name, "slot": item.slot,
            "rarity": item.rarity, "art": item.art, "image_url": item.image_url,
        }
    return out


def loadout(user_id):
    """``{slot: Item}`` for what the user is wearing."""
    rows = EquippedItem.objects.filter(user_id=user_id).select_related("user_item__item")
    return {row.slot: row.user_item.item for row in rows}
