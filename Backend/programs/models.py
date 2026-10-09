from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class Company(models.Model):
    """Company profile that can create bug bounty programs"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_profile'
    )
    company_name = models.CharField(max_length=200)
    website = models.URLField()
    description = models.TextField()
    contact_email = models.EmailField()
    industry = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "companies"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.user.username})"

    @property
    def can_create_program(self):
        """Check if company can create programs"""
        return self.is_verified


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='programs'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    scope_type = models.CharField(max_length=20, choices=SCOPE_TYPE_CHOICES, default='public')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    bounty_policy = models.TextField(blank=True)
    min_bounty = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    max_bounty = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    allow_anonymous = models.BooleanField(default=False)
    require_ndas = models.BooleanField(default=False)
    invitation_only = models.BooleanField(default=False)
    requires_application = models.BooleanField(default=False)

    testing_guidelines = models.TextField(blank=True)
    report_guidelines = models.TextField(blank=True)
    disclosure_policy = models.TextField(blank=True)

    # Cached stats — kept in sync via reports/signals.py
    total_reports = models.IntegerField(default=0)
    total_bounties = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_severity_score = models.FloatField(default=0)
    avg_time_to_triage = models.FloatField(default=0)
    avg_time_to_resolution = models.FloatField(default=0)

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

    def _generate_unique_slug(self):
        base = slugify(self.name)
        slug = base
        counter = 1
        qs = Program.objects.exclude(pk=self.pk) if self.pk else Program.objects.all()
        while qs.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
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
        if self.end_date and self.end_date < timezone.now().date():
            return False
        return True

    @property
    def bounty_range(self):
        if self.min_bounty and self.max_bounty:
            return f"${self.min_bounty} - ${self.max_bounty}"
        if self.min_bounty:
            return f"From ${self.min_bounty}"
        if self.max_bounty:
            return f"Up to ${self.max_bounty}"
        return "Not specified"

    def refresh_stats(self):
        """Recompute cached stat fields from live report data."""
        from django.db.models import Count, Sum, Avg
        from reports.models import BugReport

        reports = BugReport.objects.filter(program=self)
        agg = reports.aggregate(
            total=Count('id'),
            bounties=Sum('bounty_amount'),
            avg_severity=Avg('severity_score'),
            avg_triage=Avg('time_to_triage'),
            avg_resolution=Avg('time_to_resolution'),
        )
        self.total_reports = agg['total'] or 0
        self.total_bounties = agg['bounties'] or 0
        self.avg_severity_score = agg['avg_severity'] or 0
        self.avg_time_to_triage = agg['avg_triage'] or 0
        self.avg_time_to_resolution = agg['avg_resolution'] or 0
        self.save(update_fields=[
            'total_reports', 'total_bounties', 'avg_severity_score',
            'avg_time_to_triage', 'avg_time_to_resolution',
        ])


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Invitation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Stats snapshot
# ---------------------------------------------------------------------------

class ProgramStats(models.Model):
    """
    Daily stats snapshot. Populate via ProgramStats.snapshot_for(program)
    from a nightly Celery beat task or management command.
    """
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='stats_snapshots')
    date = models.DateField()

    total_reports = models.IntegerField(default=0)
    new_reports = models.IntegerField(default=0)
    resolved_reports = models.IntegerField(default=0)

    total_bounties = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_bounty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    avg_time_to_triage = models.FloatField(default=0)
    avg_time_to_resolution = models.FloatField(default=0)
    avg_time_to_bounty = models.FloatField(default=0)

    critical_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    medium_count = models.IntegerField(default=0)
    low_count = models.IntegerField(default=0)
    info_count = models.IntegerField(default=0)

    active_researchers = models.IntegerField(default=0)
    new_researchers = models.IntegerField(default=0)

    class Meta:
        unique_together = ['program', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.program.name} — {self.date}"

    @property
    def total_vulnerabilities(self):
        return (
            self.critical_count + self.high_count +
            self.medium_count + self.low_count + self.info_count
        )

    @classmethod
    def snapshot_for(cls, program, date=None):
        from django.db.models import Count, Sum, Avg
        from reports.models import BugReport

        if date is None:
            date = timezone.now().date()

        reports = BugReport.objects.filter(program=program)
        today_reports = reports.filter(created_at__date=date)
        resolved_today = reports.filter(status='resolved', updated_at__date=date)
        severity_counts = {
            row['severity']: row['count']
            for row in reports.values('severity').annotate(count=Count('id'))
        }
        agg = reports.aggregate(
            total_bounties=Sum('bounty_amount'),
            avg_bounty=Avg('bounty_amount'),
            avg_triage=Avg('time_to_triage'),
            avg_resolution=Avg('time_to_resolution'),
            # time_to_bounty does not exist on BugReport yet; omit until the
            # field is added and avg_time_to_bounty will remain 0 in snapshots.
        )

        snapshot, _ = cls.objects.update_or_create(
            program=program,
            date=date,
            defaults={
                'total_reports': reports.count(),
                'new_reports': today_reports.count(),
                'resolved_reports': resolved_today.count(),
                'total_bounties': agg['total_bounties'] or 0,
                'avg_bounty': agg['avg_bounty'] or 0,
                'avg_time_to_triage': agg['avg_triage'] or 0,
                'avg_time_to_resolution': agg['avg_resolution'] or 0,
                'avg_time_to_bounty': 0,  # field not yet on BugReport
                'critical_count': severity_counts.get('critical', 0),
                'high_count': severity_counts.get('high', 0),
                'medium_count': severity_counts.get('medium', 0),
                'low_count': severity_counts.get('low', 0),
                'info_count': severity_counts.get('info', 0),
                'active_researchers': reports.values('reporter').distinct().count(),
                'new_researchers': today_reports.values('reporter').distinct().count(),
            }
        )
        return snapshot


# ---------------------------------------------------------------------------
# Favorite
# ---------------------------------------------------------------------------

class ProgramFavorite(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='favorites')
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_programs'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['program', 'researcher']
        ordering = ['-created_at']
        indexes = [models.Index(fields=['researcher', 'created_at'])]

    def __str__(self):
        return f"{self.researcher.username} ★ {self.program.name}"


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

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