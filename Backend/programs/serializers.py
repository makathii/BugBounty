from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class Program(models.Model):
    SCOPE_TYPE_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('vdp', 'VDP - Vulnerability Disclosure Program'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
    ]

    company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='programs'
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)

    scope_type = models.CharField(max_length=20, choices=SCOPE_TYPE_CHOICES, default='public')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Bounty information
    bounty_policy = models.TextField(blank=True)
    min_bounty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    max_bounty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    # Program dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Program settings
    allow_anonymous = models.BooleanField(default=False)
    require_ndas = models.BooleanField(default=False)
    invitation_only = models.BooleanField(default=False)
    requires_application = models.BooleanField(default=False)

    # Guidelines
    testing_guidelines = models.TextField(blank=True)
    report_guidelines = models.TextField(blank=True)
    disclosure_policy = models.TextField(blank=True)

    # Stats (cached for performance)
    total_reports = models.IntegerField(default=0)
    total_bounties = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_severity_score = models.FloatField(default=0)
    avg_time_to_triage = models.FloatField(default=0)  # in hours
    avg_time_to_resolution = models.FloatField(default=0)  # in hours

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'scope_type']),
            models.Index(fields=['company', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.company.username})"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
            # Ensure slug is unique
            counter = 1
            original_slug = self.slug
            while Program.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        # Set published_at when status changes to active
        if self.status == 'active' and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def can_accept_submissions(self):
        if not self.is_active:
            return False

        # Check if program has ended
        if self.end_date and self.end_date < timezone.now().date():
            return False

        return True

    @property
    def bounty_range(self):
        if self.min_bounty and self.max_bounty:
            return f"${self.min_bounty} - ${self.max_bounty}"
        elif self.min_bounty:
            return f"From ${self.min_bounty}"
        elif self.max_bounty:
            return f"Up to ${self.max_bounty}"
        else:
            return "Not specified"


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
    target_type = models.CharField(max_length=50, choices=TARGET_TYPE_CHOICES, default='web_application')
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
        indexes = [
            models.Index(fields=['program', 'is_in_scope']),
        ]

    def __str__(self):
        status = "IN" if self.is_in_scope else "OUT"
        return f"{status} Scope: {self.target}"


class ProgramInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('revoked', 'Revoked'),
    ]

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='invitations')
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='program_invitations'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations'
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['program', 'researcher']
        indexes = [
            models.Index(fields=['program', 'status']),
            models.Index(fields=['researcher', 'status']),
        ]

    def __str__(self):
        return f"{self.researcher.username} -> {self.program.name} ({self.status})"


class ProgramApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='applications')
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='program_applications'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    qualifications = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviewed_applications'
    )
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['program', 'researcher']
        indexes = [
            models.Index(fields=['program', 'status']),
            models.Index(fields=['researcher', 'status']),
        ]

    def __str__(self):
        return f"{self.researcher.username} applied to {self.program.name} ({self.status})"


class ProgramStats(models.Model):
    """Periodic stats snapshot for programs"""
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='stats_snapshots')
    date = models.DateField()

    # Report counts
    total_reports = models.IntegerField(default=0)
    new_reports = models.IntegerField(default=0)
    resolved_reports = models.IntegerField(default=0)

    # Bounty statistics
    total_bounties = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_bounty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Time metrics (in hours)
    avg_time_to_triage = models.FloatField(default=0)
    avg_time_to_resolution = models.FloatField(default=0)
    avg_time_to_bounty = models.FloatField(default=0)

    # Severity distribution
    critical_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    medium_count = models.IntegerField(default=0)
    low_count = models.IntegerField(default=0)
    info_count = models.IntegerField(default=0)

    # Researcher engagement
    active_researchers = models.IntegerField(default=0)
    new_researchers = models.IntegerField(default=0)

    class Meta:
        unique_together = ['program', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['program', 'date']),
        ]

    def __str__(self):
        return f"{self.program.name} stats on {self.date}"

    @property
    def total_vulnerabilities(self):
        return self.critical_count + self.high_count + self.medium_count + self.low_count + self.info_count


class ProgramFavorite(models.Model):
    """Allow researchers to favorite programs"""
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='favorites')
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_programs'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['program', 'researcher']
        indexes = [
            models.Index(fields=['researcher', 'created_at']),
        ]

    def __str__(self):
        return f"{self.researcher.username} favorites {self.program.name}"


class ProgramNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_report', 'New Report'),
        ('report_status_change', 'Report Status Change'),
        ('program_update', 'Program Update'),
        ('new_scope', 'New Scope Added'),
        ('bounty_paid', 'Bounty Paid'),
        ('application_update', 'Application Status Update'),
        ('invitation', 'New Invitation'),
    ]

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='program_notifications')
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
        return f"{self.title} - {self.user.username}"