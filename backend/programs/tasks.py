from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300,
    max_retries=5, ignore_result=True,
)
def send_program_invitation_notification(invitation_id):
    """Tell a researcher they were invited to a private program."""
    from .models import ProgramInvitation

    try:
        invitation = ProgramInvitation.objects.select_related(
            "program", "researcher", "invited_by"
        ).get(pk=invitation_id)
    except ProgramInvitation.DoesNotExist:
        return
    researcher = invitation.researcher
    if not researcher.email or invitation.status != "pending":
        return

    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    who = invitation.invited_by.username if invitation.invited_by else "A company"
    note = f"\n\nMessage from {who}:\n{invitation.message}" if invitation.message else ""
    send_mail(
        f"You're invited to the private program {invitation.program.name}",
        (
            f"Hi {researcher.first_name or researcher.username},\n\n"
            f"{who} invited you to the private program \"{invitation.program.name}\"."
            f"{note}\n\n"
            f"Look at it and accept (or decline) here: {base}/programs/{invitation.program_id}\n"
        ),
        settings.DEFAULT_FROM_EMAIL,
        [researcher.email],
    )
