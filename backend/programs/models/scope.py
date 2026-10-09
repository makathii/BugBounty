from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .program import Program


class Scope(models.Model):
    TARGET_TYPE_CHOICES = [
        ('web_application', 'Web Application'),
        ('mobile_app', 'Mobile Application'),
        ('api', 'API/Web Service'),
        ('iot', 'IoT Device'),
        ('network', 'Network Infrastructure'),
        ('hardware', 'Hardware'),
        ('source_code', 'Source Code'),
        ('social_engineering', 'Social Engineering'),
        ('physical_security', 'Physical Security'),
        ('other', 'Other'),
    ]

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='scopes')
    target = models.CharField(max_length=500)
    target_type = models.CharField(
        max_length=50, choices=TARGET_TYPE_CHOICES, default='web_application'
    )
    is_in_scope = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    bounty_multiplier = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_in_scope', 'target_type', 'target']
        indexes = [models.Index(fields=['program', 'is_in_scope'])]

    def __str__(self):
        label = "IN" if self.is_in_scope else "OUT"
        return f"[{label}] {self.target} ({self.get_target_type_display()})"
