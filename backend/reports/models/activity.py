from django.conf import settings
from django.db import models

from .bugreport import BugReport


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('status_change', 'Status Change'),
        ('comment', 'Comment'),
        ('assignment', 'Assignment'),
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('reopen', 'Reopen'),
        ('mark_duplicate', 'Mark as Duplicate'),
    ]

    report = models.ForeignKey(BugReport, on_delete=models.CASCADE, related_name="activity_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict)  # Store additional data like old_status, new_status, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    steps_to_reproduce = models.TextField(blank=True, null=True)
    impact = models.TextField(blank=True, null=True)
    vulnerability_type = models.CharField(max_length=100, blank=True)
    affected_url = models.URLField(blank=True)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.report.title}"
