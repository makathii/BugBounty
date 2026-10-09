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


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300,
    max_retries=5, ignore_result=True,
)
def send_comment_notification(comment_id):
    """Tell the people in a thread that someone commented or replied.

    Public comments go to the reporter, the assigned triager and the parent
    comment's author; internal notes only reach staff (assignee / parent author),
    never the researcher. The author is never emailed about their own comment.
    """
    from .models import Comment

    try:
        comment = Comment.objects.select_related(
            "author", "report__reporter", "report__assigned_to", "parent__author",
        ).get(pk=comment_id)
    except Comment.DoesNotExist:
        return

    report = comment.report
    people = [report.assigned_to, comment.parent.author if comment.parent_id else None]
    if not comment.is_internal:
        people.append(report.reporter)

    emails = sorted({
        u.email for u in people
        if u is not None and u.email and u.id != comment.author_id
    })
    if not emails:
        return

    who = comment.author.username if comment.author else "Someone"
    kind = "internal note" if comment.is_internal else ("reply" if comment.parent_id else "comment")
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    message = (
        f"{who} posted a {kind} on \"{report.title}\":\n\n"
        f"{comment.text[:500]}\n\n"
        f"View the thread: {base}/reports/{report.id}\n"
    )
    send_mail(
        f"New {kind} on report: {report.title}",
        message,
        settings.DEFAULT_FROM_EMAIL,
        emails,
    )
