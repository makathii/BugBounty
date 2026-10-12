from django.conf import settings
from django.db import models


class Item(models.Model):
    """A cosmetic for a researcher's character, bought with wallet points."""

    HAT, FACE, BODY, PET, BACKGROUND = "hat", "face", "body", "pet", "background"
    SLOT_CHOICES = [
        (HAT, "Hat"), (FACE, "Face"), (BODY, "Body"), (PET, "Pet"), (BACKGROUND, "Background"),
    ]
    COMMON, RARE, EPIC, LEGENDARY = "common", "rare", "epic", "legendary"
    RARITY_CHOICES = [
        (COMMON, "Common"), (RARE, "Rare"), (EPIC, "Epic"), (LEGENDARY, "Legendary"),
    ]

    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=300, blank=True)
    slot = models.CharField(max_length=12, choices=SLOT_CHOICES)
    rarity = models.CharField(max_length=10, choices=RARITY_CHOICES, default=COMMON)
    # 0 = free (starter items).
    price = models.PositiveIntegerField(default=0)
    # Researchers below this level see the item but cannot buy it yet.
    min_level = models.PositiveSmallIntegerField(default=1)
    # Placeholder art until real artwork exists: an emoji. ``image_url`` overrides it later.
    art = models.CharField(max_length=16, blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    # Retire an item from the shop without deleting it (owners keep it).
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "price", "id"]
        indexes = [models.Index(fields=["is_active", "slot"], name="store_item_active_slot")]

    def __str__(self):
        return f"{self.name} ({self.price} pts)"


class UserItem(models.Model):
    """An item a researcher owns (their inventory). One row per user per item."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventory",
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="owners")
    purchased_at = models.DateTimeField(auto_now_add=True)
    # What was actually paid (the price can change later) and the wallet row for refunds.
    price_paid = models.PositiveIntegerField(default=0)
    transaction = models.OneToOneField(
        "wallet.WalletTransaction", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-purchased_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="store_own_item_once"),
        ]

    def __str__(self):
        return f"{self.user} owns {self.item.name}"


class EquippedItem(models.Model):
    """What a researcher's character is wearing: at most one owned item per slot."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="equipped",
    )
    slot = models.CharField(max_length=12, choices=Item.SLOT_CHOICES)
    user_item = models.OneToOneField(UserItem, on_delete=models.CASCADE, related_name="equipped")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "slot"], name="store_one_item_per_slot"),
        ]

    def __str__(self):
        return f"{self.user} wears {self.user_item.item.name} ({self.slot})"
