from django.conf import settings
from django.db import models

from .program import Program


class ProgramInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('revoked', 'Revoked'),
    ]

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='invitations')
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='program_invitations'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='sent_invitations'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['program', 'researcher']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['program', 'status']),
            models.Index(fields=['researcher', 'status']),
        ]

    def __str__(self):
        return f"{self.researcher.username} → {self.program.name} ({self.status})"

    def accept(self):
        if self.status != 'pending':
            raise ValueError(f"Cannot accept an invitation that is already '{self.status}'.")
        self.status = 'accepted'
        self.save(update_fields=['status', 'updated_at'])

    def reject(self):
        if self.status != 'pending':
            raise ValueError(f"Cannot reject an invitation that is already '{self.status}'.")
        self.status = 'rejected'
        self.save(update_fields=['status', 'updated_at'])

    def revoke(self):
        if self.status not in ('pending', 'accepted'):
            raise ValueError(f"Cannot revoke an invitation that is already '{self.status}'.")
        self.status = 'revoked'
        self.save(update_fields=['status', 'updated_at'])
