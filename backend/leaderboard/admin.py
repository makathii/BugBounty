from django.contrib import admin

from .models import ScoreEvent


@admin.register(ScoreEvent)
class ScoreEventAdmin(admin.ModelAdmin):
    list_display = ("researcher", "report", "program", "points", "severity", "awarded_at")
    list_filter = ("severity", "program", "awarded_at")
    search_fields = ("researcher__username", "report__title")
    raw_id_fields = ("researcher", "report", "program")
    date_hierarchy = "awarded_at"
    # The ledger is maintained by signals; treat it as read-only in admin so a
    # stray manual edit can't desync it from report state.
    readonly_fields = ("researcher", "report", "program", "points", "severity",
                       "awarded_at", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False
