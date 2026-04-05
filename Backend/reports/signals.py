from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import BugReport


@receiver(post_save, sender=BugReport)
def on_report_saved(sender, instance, created, **kwargs):
    updated = False

    # --- Update severity_score based on severity ---
    if instance.severity:
        severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        score = severity_map.get(instance.severity, 0)
        if instance.severity_score != score:
            instance.severity_score = score
            updated = True

    # --- Set time_to_triage if status changed to triaged ---
    if instance.status == 'triaged' and instance.time_to_triage is None:
        delta = (timezone.now() - instance.created_at).total_seconds() / 3600
        instance.time_to_triage = round(delta, 2)
        updated = True

    # --- Set time_to_resolution if status changed to resolved/closed ---
    if instance.status in ('resolved', 'closed') and instance.time_to_resolution is None:
        delta = (timezone.now() - instance.created_at).total_seconds() / 3600
        instance.time_to_resolution = round(delta, 2)
        updated = True

    # Save only if any field changed
    if updated:
        instance.save(update_fields=[
            f for f in ['severity_score', 'time_to_triage', 'time_to_resolution'] if getattr(instance, f) is not None
        ])

    # --- Refresh cached program stats ---
    if instance.program_id:
        try:
            instance.program.refresh_stats()
        except Exception:
            pass


@receiver(post_delete, sender=BugReport)
def on_report_deleted(sender, instance, **kwargs):
    if instance.program_id:
        try:
            instance.program.refresh_stats()
        except Exception:
            pass