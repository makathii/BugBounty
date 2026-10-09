from celery import shared_task
from django.core.management import call_command


@shared_task(ignore_result=True)
def purge_audit_logs():
    """Daily retention sweep (scheduled by Celery beat)."""
    call_command("purge_audit_logs")
