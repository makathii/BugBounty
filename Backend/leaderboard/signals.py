"""
Keep the ScoreEvent ledger in sync with BugReport state.

This lives in its own app rather than in reports/signals.py to keep the
scoring concern self-contained: removing the leaderboard app removes all of
its behaviour with it.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from reports.models import BugReport
from .services import sync_report_score


@receiver(post_save, sender=BugReport, dispatch_uid="leaderboard_sync_on_save")
def on_report_saved(sender, instance, **kwargs):
    # reports/signals.py may re-save the instance to backfill severity_score /
    # timing fields; sync_report_score is idempotent so the extra call is fine.
    sync_report_score(instance)


@receiver(post_delete, sender=BugReport, dispatch_uid="leaderboard_sync_on_delete")
def on_report_deleted(sender, instance, **kwargs):
    # The OneToOne FK is CASCADE, so the ScoreEvent is already gone by the time
    # this fires — nothing to do, but the hook is here for symmetry / clarity.
    pass
