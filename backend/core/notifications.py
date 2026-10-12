"""
In-app notifications (the bell in the navbar). Emails are sent separately by Celery tasks; these
rows are created synchronously so they never depend on mail or a broker being up.
"""
import logging

from django.db import transaction

logger = logging.getLogger(__name__)


def notify(user, notification_type, title, message, link="", program=None):
    """Create a notification for ``user``; ``link`` is a frontend path such as ``/reports/5``.

    Never raises: a notification problem must not undo the action that caused it.
    """
    if user is None:
        return None
    from programs.models import ProgramNotification

    try:
        with transaction.atomic():  # savepoint, so a failure can't poison the caller's transaction
            return ProgramNotification.notify(
                user=user,
                notification_type=notification_type,
                title=title[:200],
                message=message,
                program=program,
                data={"link": link} if link else {},
            )
    except Exception:
        logger.exception("Could not create a %s notification for user %s", notification_type, user.pk)
        return None
