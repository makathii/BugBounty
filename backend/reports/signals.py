from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.tasks import enqueue_after_commit

from .models import BugReport
from .tasks import refresh_program_stats


@receiver(post_save, sender=BugReport)
def on_report_saved(sender, instance, created, **kwargs):
    """
    Refresh cached stats for the program(s) a save actually affected.

    Derived fields (severity_score, time_to_*) are computed in
    BugReport.save(), so there is no re-save here. ``_stats_programs`` is empty
    when nothing stats-relevant changed (e.g. only verification_notes edited),
    and holds both the old and new program when a report is moved.

    The refresh runs as a Celery task after commit (inline when no broker is
    configured). With a broker, stats are eventually consistent: they update
    when the worker picks the task up, not before the HTTP response.
    """
    program_ids = getattr(instance, '_stats_programs', None)
    if program_ids is None:  # raw/fixture load etc.: fall back to current program
        program_ids = {instance.program_id} if instance.program_id else set()

    for program_id in program_ids:
        enqueue_after_commit(refresh_program_stats, program_id)


@receiver(post_delete, sender=BugReport)
def on_report_deleted(sender, instance, **kwargs):
    if instance.program_id:
        enqueue_after_commit(refresh_program_stats, instance.program_id)
