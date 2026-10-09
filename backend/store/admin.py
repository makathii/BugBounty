from django.contrib import admin, messages

from . import services
from .models import EquippedItem, Item, UserItem


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "slot", "rarity", "price", "min_level", "is_active", "sort_order")
    list_filter = ("slot", "rarity", "is_active")
    list_editable = ("price", "is_active", "sort_order")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(UserItem)
class UserItemAdmin(admin.ModelAdmin):
    """Read-only inventory; the one allowed change is refunding a purchase."""

    list_display = ("user", "item", "price_paid", "purchased_at")
    list_filter = ("item__slot",)
    search_fields = ("user__username", "item__name")
    actions = ["refund_selected"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # use the refund action so the points go back

    @admin.action(description="Refund selected purchases (returns the points)")
    def refund_selected(self, request, queryset):
        count = 0
        for user_item in queryset:
            services.refund(user_item)
            count += 1
        self.message_user(request, f"Refunded {count} purchase(s).", messages.SUCCESS)


@admin.register(EquippedItem)
class EquippedItemAdmin(admin.ModelAdmin):
    list_display = ("user", "slot", "user_item")
    list_filter = ("slot",)
    search_fields = ("user__username",)
