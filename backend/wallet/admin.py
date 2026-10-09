from django.contrib import admin

from . import services
from .models import WalletTransaction


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Append-only ledger: staff can add an adjustment (with a reason) but never edit or delete."""

    list_display = ("user", "amount", "kind", "reason", "created_by", "created_at")
    list_filter = ("kind",)
    search_fields = ("user__username", "reason", "reference")
    autocomplete_fields = ("user",)
    fields = ("user", "amount", "reason")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("user", "amount", "reason")
        return ("user", "amount", "kind", "reason", "reference", "created_by", "created_at")

    def save_model(self, request, obj, form, change):
        # Go through the service so the row gets its kind/created_by and the same locking.
        obj.pk = services.adjust(
            obj.user, obj.amount, obj.reason, created_by=request.user,
        ).pk
