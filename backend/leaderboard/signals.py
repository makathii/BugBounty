"""
Keep the ScoreEvent ledger in sync with BugReport state.

This lives in its own app rather than in reports/signals.py to keep the
scoring concern self-contained: removing the leaderboard app removes all of
its behaviour with it.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.tasks import enqueue_after_commit
from reports.models import BugReport
from reports.tasks import refresh_program_stats
from .models import ScoreEvent
from .services import bump_cache_version, sync_report_score


@receiver(post_save, sender=BugReport, dispatch_uid="leaderboard_sync_on_save")
def on_report_saved(sender, instance, **kwargs):
    # BugReport.save() flags whether any score-relevant field changed; skip the
    # ledger lookup otherwise. Missing flag (raw load) -> sync to be safe.
    if getattr(instance, "_score_dirty", True):
        sync_report_score(instance)


@receiver(post_delete, sender=BugReport, dispatch_uid="leaderboard_sync_on_delete")
def on_report_deleted(sender, instance, **kwargs):
    # The OneToOne FK is CASCADE, so the ScoreEvent is already gone by the time
    # this fires — nothing to do, but the hook is here for symmetry / clarity.
    pass


@receiver(post_save, sender=ScoreEvent, dispatch_uid="leaderboard_cache_bump_on_save")
@receiver(post_delete, sender=ScoreEvent, dispatch_uid="leaderboard_cache_bump_on_delete")
def invalidate_leaderboard_cache(sender, **kwargs):
    # Covers every ledger mutation, including the cascade when a report is deleted.
    bump_cache_version()


@receiver(post_save, sender=ScoreEvent, dispatch_uid="leaderboard_program_stats_on_save")
@receiver(post_delete, sender=ScoreEvent, dispatch_uid="leaderboard_program_stats_on_delete")
def refresh_program_points(sender, instance, **kwargs):
    # A program's total/average points come from the ledger, so refresh them whenever
    # the ledger changes (the report's own save may run before its ScoreEvent exists).
    if instance.program_id:
        enqueue_after_commit(refresh_program_stats, instance.program_id)
