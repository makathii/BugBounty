from django.apps import AppConfig


class BadgesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "badges"
    verbose_name = "Badges"

    def ready(self):
        from . import signals  # noqa: F401  (connects the ScoreEvent receivers)
