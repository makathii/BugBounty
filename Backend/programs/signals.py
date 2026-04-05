from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ProgramInvitation, ProgramApplication, ProgramNotification


@receiver(post_save, sender=ProgramInvitation)
def on_invitation_created(sender, instance, created, **kwargs):
    if not created:
        return
    ProgramNotification.notify(
        user=instance.researcher,
        notification_type='invitation',
        title=f"You've been invited to {instance.program.name}",
        message=(
            instance.message or
            f"{instance.invited_by.username} invited you to join {instance.program.name}."
        ),
        program=instance.program,
    )


@receiver(post_save, sender=ProgramApplication)
def on_application_status_changed(sender, instance, created, **kwargs):
    if created:
        return  # no notification on submission, only on review outcome

    if instance.status == 'approved':
        ProgramNotification.notify(
            user=instance.researcher,
            notification_type='application_update',
            title=f"Application approved — {instance.program.name}",
            message=f"Your application to {instance.program.name} has been approved. You can now submit reports.",
            program=instance.program,
        )
    elif instance.status == 'rejected':
        ProgramNotification.notify(
            user=instance.researcher,
            notification_type='application_update',
            title=f"Application update — {instance.program.name}",
            message=f"Your application to {instance.program.name} was not approved.",
            program=instance.program,
        )