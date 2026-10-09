from django.conf import settings
from django.db import models

from .program import Program


class ProgramNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_report', 'New Report'),
        ('report_status_change', 'Report Status Change'),
        ('program_update', 'Program Update'),
        ('new_scope', 'New Scope Added'),
        ('points_awarded', 'Points Awarded'),
        ('application_update', 'Application Status Update'),
        ('invitation', 'New Invitation'),
    ]

    # nullable — some notifications are user-level, not tied to a program
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='program_notifications'
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read', 'created_at']),
            models.Index(fields=['program', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title} → {self.user.username}"

    def mark_read(self):
        if not self.read:
            self.read = True
            self.save(update_fields=['read'])

    @classmethod
    def notify(cls, user, notification_type, title, message, program=None, data=None):
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            program=program,
            data=data or {},
        )
