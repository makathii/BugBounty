"""
Points wallet logic. Every balance read and every mutation goes through here.

    balance = lifetime earned (leaderboard.ScoreEvent)  +  sum(WalletTransaction.amount)
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum

from leaderboard.levels import level_for
from leaderboard.models import ScoreEvent

from .models import WalletTransaction


class InsufficientPoints(Exception):
    """The wallet does not hold enough points for the requested spend."""

    def __init__(self, balance, needed):
        self.balance = balance
        self.needed = needed
        super().__init__(f"Not enough points: have {balance}, need {needed}.")


def lifetime_earned(user):
    """Total points ever earned from reports (what the leaderboard ranks by)."""
    return ScoreEvent.objects.filter(researcher=user).aggregate(t=Sum("points"))["t"] or 0


def balance(user):
    """Spendable points: earned plus the net of purchases, refunds and adjustments."""
    net = WalletTransaction.objects.filter(user=user).aggregate(t=Sum("amount"))["t"] or 0
    return lifetime_earned(user) + net


def summary(user):
    """Balance with its breakdown, for the wallet page."""
    earned = lifetime_earned(user)
    totals = WalletTransaction.objects.filter(user=user).aggregate(
        net=Sum("amount"),
        spent=Sum("amount", filter=Q(amount__lt=0)),
    )
    net = totals["net"] or 0
    return {
        "balance": earned + net,
        "lifetime_earned": earned,
        "total_spent": -(totals["spent"] or 0),
        "level": level_for(earned),
    }


def _add(user, amount, kind, reason, reference="", created_by=None):
    return WalletTransaction.objects.create(
        user=user, amount=amount, kind=kind, reason=reason[:200],
        reference=reference[:100], created_by=created_by,
    )


def spend(user, amount, reason, reference=""):
    """
    Spend ``amount`` points. Raises ``InsufficientPoints`` if the balance is too low.

    The user row is locked for the duration, so two simultaneous purchases cannot
    both pass the balance check and overdraw the wallet.
    """
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValueError("amount must be a positive whole number of points")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        current = balance(user)
        if current < amount:
            raise InsufficientPoints(current, amount)
        return _add(user, -amount, WalletTransaction.PURCHASE, reason, reference)


def refund(purchase, reason="Refund"):
    """Give the points of a purchase back (once). Returns the refund row."""
    if purchase.kind != WalletTransaction.PURCHASE or purchase.amount >= 0:
        raise ValueError("only purchases can be refunded")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=purchase.user_id)
        ref = f"refund:{purchase.pk}"
        if WalletTransaction.objects.filter(user_id=purchase.user_id, reference=ref).exists():
            raise ValueError("this purchase was already refunded")
        return _add(purchase.user, -purchase.amount, WalletTransaction.REFUND, reason, ref)


def adjust(user, amount, reason, created_by=None):
    """Staff correction: grant (positive) or claw back (negative) points, with a reason."""
    if not isinstance(amount, int) or isinstance(amount, bool) or amount == 0:
        raise ValueError("amount must be a non-zero whole number of points")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        return _add(user, amount, WalletTransaction.ADJUSTMENT, reason, created_by=created_by)
