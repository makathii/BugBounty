import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300,
    max_retries=5, ignore_result=True,
)
def refresh_program_stats(program_id):
    """Recompute a program's cached stats. Idempotent, so retries/duplicates are safe."""
    from programs.models import Program
    Program.refresh_stats_for(program_id)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300,
    max_retries=5, ignore_result=True,
)
def send_report_submission_notification(report_id):
    """Email Admin users about a newly submitted report."""
    from django.contrib.auth.models import User
    from .models import BugReport

    try:
        report = BugReport.objects.select_related("reporter").get(pk=report_id)
    except BugReport.DoesNotExist:
        return  # deleted before the worker ran

    admin_emails = list(
        User.objects.filter(groups__name="Admin").exclude(email="")
        .values_list("email", flat=True).distinct()
    )
    if not admin_emails:
        return

    message = (
        "New bug report has been submitted:\n\n"
        f"Title: {report.title}\n"
        f"Reporter: {report.reporter.username}\n"
        f"Severity: {report.severity}\n"
        f"Description: {report.description[:200]}...\n\n"
        f"View and manage at: http://localhost:8000/admin/reports/bugreport/{report.id}/\n"
    )
    send_mail(
        f"New Bug Report Submitted: {report.title}",
        message,
        settings.DEFAULT_FROM_EMAIL,
        admin_emails,
    )
