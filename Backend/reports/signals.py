from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import BugReport


@receiver(post_save, sender=BugReport)
def on_report_saved(sender, instance, created, **kwargs):
    """
    Refresh cached stats for the program(s) a save actually affected.

    Derived fields (severity_score, time_to_*) are computed in
    BugReport.save(), so there is no re-save here. ``_stats_programs`` is empty
    when nothing stats-relevant changed (e.g. only verification_notes edited),
    and holds both the old and new program when a report is moved.

    Errors are deliberately not swallowed: a failing stats query means the
    surrounding transaction is already unusable on PostgreSQL.
    """
    from programs.models import Program

    program_ids = getattr(instance, '_stats_programs', None)
    if program_ids is None:  # raw/fixture load etc.: fall back to current program
        program_ids = {instance.program_id} if instance.program_id else set()

    for program_id in program_ids:
        Program.refresh_stats_for(program_id)


@receiver(post_delete, sender=BugReport)
def on_report_deleted(sender, instance, **kwargs):
    from programs.models import Program

    if instance.program_id:
        Program.refresh_stats_for(instance.program_id)
