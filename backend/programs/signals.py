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
        data={'link': f'/programs/{instance.program_id}'},
    )


@receiver(post_save, sender=ProgramApplication)
def on_application_status_changed(sender, instance, created, **kwargs):
    if created:
        # the company is told about every new application (the researcher gets the outcome below)
        ProgramNotification.notify(
            user=instance.program.company,
            notification_type='application_submitted',
            title=f"New application — {instance.program.name}",
            message=f"{instance.researcher.username} applied to join {instance.program.name}.",
            program=instance.program,
            data={'link': f'/company/programs/{instance.program_id}/applications'},
        )
        return

    if instance.status == 'approved':
        ProgramNotification.notify(
            user=instance.researcher,
            notification_type='application_update',
            title=f"Application approved — {instance.program.name}",
            message=f"Your application to {instance.program.name} has been approved. You can now submit reports.",
            program=instance.program,
            data={'link': f'/programs/{instance.program_id}'},
        )
    elif instance.status == 'rejected':
        ProgramNotification.notify(
            user=instance.researcher,
            notification_type='application_update',
            title=f"Application update — {instance.program.name}",
            message=f"Your application to {instance.program.name} was not approved.",
            program=instance.program,
            data={'link': f'/programs/{instance.program_id}'},
        )
