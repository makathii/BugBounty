from rest_framework import serializers

from .models import Item


class ItemSerializer(serializers.ModelSerializer):
    """An item as the shop shows it. ``owned``/``equipped``/``can_buy`` come from the view context."""

    slot_display = serializers.CharField(source="get_slot_display", read_only=True)
    rarity_display = serializers.CharField(source="get_rarity_display", read_only=True)
    owned = serializers.SerializerMethodField()
    equipped = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()
    can_afford = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = (
            "id", "slug", "name", "description", "slot", "slot_display", "rarity",
            "rarity_display", "price", "min_level", "art", "image_url",
            "owned", "equipped", "locked", "can_afford",
        )
        read_only_fields = fields

    def get_owned(self, obj):
        return obj.pk in self.context.get("owned_ids", ())

    def get_equipped(self, obj):
        return obj.pk in self.context.get("equipped_ids", ())

    def get_locked(self, obj):
        """True when the researcher's level is below the item's requirement."""
        return self.context.get("level", 1) < obj.min_level

    def get_can_afford(self, obj):
        return self.context.get("balance", 0) >= obj.price


class LoadoutItemSerializer(serializers.ModelSerializer):
    """The minimum needed to draw an equipped item."""

    class Meta:
        model = Item
        fields = ("slug", "name", "slot", "rarity", "art", "image_url")
        read_only_fields = fields
