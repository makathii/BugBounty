from django.conf import settings
from django.db import models

from .program import Program


class ProgramApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='applications')
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='program_applications'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_applications'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    qualifications = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)
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

    def approve(self, reviewed_by, notes=''):
        if self.status != 'pending':
            raise ValueError(f"Cannot approve an application that is already '{self.status}'.")
        self.status = 'approved'
        self.reviewed_by = reviewed_by
        self.review_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'review_notes', 'updated_at'])

    def reject(self, reviewed_by, notes=''):
        if self.status != 'pending':
            raise ValueError(f"Cannot reject an application that is already '{self.status}'.")
        self.status = 'rejected'
        self.reviewed_by = reviewed_by
        self.review_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'review_notes', 'updated_at'])

    def withdraw(self):
        if self.status != 'pending':
            raise ValueError(f"Cannot withdraw an application that is already '{self.status}'.")
        self.status = 'withdrawn'
        self.save(update_fields=['status', 'updated_at'])
