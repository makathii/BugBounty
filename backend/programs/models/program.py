from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


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

    # Free-text note on how points are awarded for this program (shown to researchers).
    reward_notes = models.TextField(blank=True)
    # Optional headline range, e.g. "10 - 150 pts". Informational: actual points come
    # from the severity table plus the triager's bonus (see leaderboard.services).
    min_points = models.PositiveIntegerField(null=True, blank=True)
    max_points = models.PositiveIntegerField(null=True, blank=True)

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
    total_points = models.IntegerField(default=0)  # points awarded to researchers
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
    def points_range(self):
        if self.min_points and self.max_points:
            return f"{self.min_points} - {self.max_points} pts"
        if self.min_points:
            return f"From {self.min_points} pts"
        if self.max_points:
            return f"Up to {self.max_points} pts"
        return "Not specified"

    def refresh_stats(self):
        """Recompute cached stat fields from live report data."""
        self.refresh_stats_for(self.pk)
        self.refresh_from_db(fields=[
            'total_reports', 'total_points', 'avg_severity_score',
            'avg_time_to_triage', 'avg_time_to_resolution',
        ])

    @classmethod
    def refresh_stats_for(cls, program_id):
        """
        Recompute cached stats for one program with exactly two queries
        (one aggregate, one UPDATE) and no model fetch. Safe to call from
        signal handlers.
        """
        from django.db.models import Count, Sum, Avg
        from leaderboard.models import ScoreEvent
        from reports.models import BugReport

        points = ScoreEvent.objects.filter(program_id=program_id).aggregate(total=Sum('points'))
        agg = BugReport.objects.filter(program_id=program_id).aggregate(
            total=Count('id'),
            avg_severity=Avg('severity_score'),
            avg_triage=Avg('time_to_triage'),
            avg_resolution=Avg('time_to_resolution'),
        )
        cls.objects.filter(pk=program_id).update(
            total_reports=agg['total'] or 0,
            total_points=points['total'] or 0,
            avg_severity_score=agg['avg_severity'] or 0,
            avg_time_to_triage=agg['avg_triage'] or 0,
            avg_time_to_resolution=agg['avg_resolution'] or 0,
        )
