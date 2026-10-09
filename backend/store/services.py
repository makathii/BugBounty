"""
Store logic: buying, owning and wearing items. The API and admin go through here.

Buying is one database transaction: the points leave the wallet and the item lands in the
inventory together, or neither happens.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from leaderboard.levels import level_for
from wallet import services as wallet

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

        tx = None
        if item.price > 0:
            tx = wallet.spend(user, item.price, f"Bought {item.name}", reference=f"item:{item.pk}")
        return UserItem.objects.create(user=user, item=item, price_paid=item.price, transaction=tx)


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


def loadout(user_id):
    """``{slot: Item}`` for what the user is wearing."""
    rows = EquippedItem.objects.filter(user_id=user_id).select_related("user_item__item")
    return {row.slot: row.user_item.item for row in rows}
