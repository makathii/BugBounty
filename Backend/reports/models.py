from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

class BugReport(models.Model):
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("triaged", "Triaged"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("duplicate", "Duplicate"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True
    )
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="low")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    
    # --- fields for signals ---
    severity_score = models.IntegerField(default=0, help_text="Numeric score for severity")
    time_to_triage = models.FloatField(null=True, blank=True, help_text="Hours to triage")
    time_to_resolution = models.FloatField(null=True, blank=True, help_text="Hours to resolution")
    steps_to_reproduce = models.TextField(blank=True, null=True)
    impact = models.TextField(blank=True, null=True)
    vulnerability_type = models.CharField(max_length=100, blank=True)
    affected_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    bounty_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Prevents duplicate submissions
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates"
    )
    duplicate_reason = models.TextField(blank=True, null=True)
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_reports"
    )
    
    verification_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

    # --- Permissions / status helpers ---
    def can_be_accepted(self):
        return self.status in ['triaged', 'accepted']

    def can_be_rejected(self):
        return self.status in ['triaged', 'rejected']
class Comment(models.Model):
    report = models.ForeignKey(BugReport, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('status_change', 'Status Change'),
        ('comment', 'Comment'),
        ('assignment', 'Assignment'),
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('reopen', 'Reopen'),
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