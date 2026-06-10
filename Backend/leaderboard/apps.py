from django.apps import AppConfig


class LeaderboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "leaderboard"
    verbose_name = "Leaderboard"

    def ready(self):
        # Wire up the BugReport post_save / post_delete handlers that keep the
        # ScoreEvent ledger in sync. Imported here (not at module top) so the
        # app registry is fully populated before signals are connected.
        from . import signals  # noqa: F401
