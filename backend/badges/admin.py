from django.contrib import admin

from .models import UserBadge


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "awarded_at")
    list_filter = ("key",)
    search_fields = ("user__username", "key")
