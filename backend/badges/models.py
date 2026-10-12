from django.conf import settings
from django.db import models


class UserBadge(models.Model):
    """
    A badge a researcher has earned. The badges themselves (name, icon, rule) live in
    code, in ``badges.definitions``; only *who earned what, when* is stored.

    Earned badges are kept: if the report behind one is later rejected the badge stays,
    so achievements never flicker. (Points and levels are the live numbers.)
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges",
    )
    key = models.CharField(max_length=40)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["awarded_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "key"], name="badge_once_per_user"),
        ]

    def __str__(self):
        return f"{self.user} earned {self.key}"
