from django.conf import settings
from django.db import models


class WalletTransaction(models.Model):
    """
    One spend / refund / adjustment on a researcher's points wallet.

    Points *earned* from reports are not stored here: they live in the
    ``leaderboard.ScoreEvent`` ledger (one row per accepted report, revoked if the
    report is later rejected). The wallet balance is

        lifetime earned (ScoreEvent)  +  sum of these transactions

    so spending never lowers the leaderboard score, and earned points can never
    drift out of sync with the reports behind them. Rows here are append-only:
    to undo a purchase, add a refund row rather than editing or deleting.
    """

    PURCHASE = "purchase"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    KIND_CHOICES = [
        (PURCHASE, "Purchase"),
        (REFUND, "Refund"),
        (ADJUSTMENT, "Adjustment"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet_transactions",
    )
    # Signed: negative spends points, positive gives them back / grants them.
    amount = models.IntegerField()
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    reason = models.CharField(max_length=200)
    # Free-form pointer to what the transaction was for, e.g. "item:12" (the future store).
    reference = models.CharField(max_length=100, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "-created_at"], name="wallet_user_created")]
        constraints = [
            models.CheckConstraint(condition=~models.Q(amount=0), name="wallet_amount_nonzero"),
        ]

    def __str__(self):
        return f"{self.user} {self.amount:+d} ({self.kind})"
