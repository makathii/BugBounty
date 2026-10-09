"""Account emails (verification). One place builds the link and sends the message."""
import logging
import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_verification_email(user):
    """
    Issue a fresh email-verification token for ``user`` and email the link.

    Returns True if the message was handed to the mail backend, False if sending
    failed (the token is still stored, so "resend" works). Never raises: a broken
    mail server must not turn a successful registration into a 500.
    """
    token = secrets.token_urlsafe(32)
    profile = user.profile
    profile.email_verification_token = token
    profile.email_verification_sent_at = timezone.now()
    profile.save()

    verify_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email/{token}"
    try:
        send_mail(
            subject="Verify your email - BugBounty Platform",
            message=(
                f"Hi {user.first_name or user.username},\n\n"
                f"Please click the link below to verify your email address:\n\n{verify_url}\n\n"
                "If you didn't create an account, you can ignore this email.\n\n"
                "Best regards,\nBugBounty Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Could not send verification email to user %s", user.pk)
        return False
    return True
