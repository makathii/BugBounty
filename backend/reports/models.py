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
    # CVSS v3.1 fields (populated via the /cvss_score/ endpoint)
    cvss_vector = models.CharField(max_length=100, blank=True, default='', help_text="CVSS v3.1 vector string")
    cvss_score = models.FloatField(null=True, blank=True, help_text="CVSS v3.1 base score (0.0–10.0)")
    cvss_severity = models.CharField(max_length=20, blank=True, default='', help_text="CVSS severity label")

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

    class Meta:
        indexes = [
            models.Index(fields=["status", "-created_at"], name="rpt_status_created"),
            models.Index(fields=["program", "status"], name="rpt_program_status"),
            models.Index(fields=["program", "-created_at"], name="rpt_program_created"),
            models.Index(fields=["reporter", "-created_at"], name="rpt_reporter_created"),
            models.Index(fields=["assigned_to", "status"], name="rpt_assignee_status"),
            models.Index(fields=["-created_at"], name="rpt_created"),
            models.Index(fields=["affected_url"], name="rpt_url"),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    # ------------------------------------------------------------------
    # Derived fields + change tracking
    #
    # Derived fields (severity_score, time_to_*) are computed here, before the
    # row is written, instead of in a post_save handler that re-saved the
    # instance (a second UPDATE that also re-fired every post_save receiver).
    #
    # We also remember the tracked values as loaded so downstream receivers
    # (program stats, leaderboard) can skip work when nothing they depend on
    # changed. See ``_stats_programs`` / ``_score_dirty``, set by save().
    # ------------------------------------------------------------------
    SEVERITY_SCORES = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
    _TRACKED = ('program_id', 'severity', 'status', 'bounty_amount',
                'reporter_id', 'duplicate_of_id')
    _STATS_TRACKED = ('program_id', 'severity', 'status', 'bounty_amount')
    _SCORE_TRACKED = ('program_id', 'severity', 'status', 'reporter_id', 'duplicate_of_id')

    @classmethod
    def from_db(cls, db, field_names, values):
        inst = super().from_db(db, field_names, values)
        inst._orig = {k: inst.__dict__[k] for k in cls._TRACKED if k in inst.__dict__}
        return inst

    def _apply_derived_fields(self):
        """Fill severity_score / time_to_* from current state. Returns changed field names."""
        from django.utils import timezone
        changed = []

        score = self.SEVERITY_SCORES.get(self.severity, 0) if self.severity else self.severity_score
        if self.severity and self.severity_score != score:
            self.severity_score = score
            changed.append('severity_score')

        def hours_since_created():
            if self.created_at is None:  # first save: created_at is stamped during INSERT
                return 0.0
            return round((timezone.now() - self.created_at).total_seconds() / 3600, 2)

        if self.status == 'triaged' and self.time_to_triage is None:
            self.time_to_triage = hours_since_created()
            changed.append('time_to_triage')
        if self.status in ('resolved', 'closed') and self.time_to_resolution is None:
            self.time_to_resolution = hours_since_created()
            changed.append('time_to_resolution')
        return changed

    def _changed_vs_orig(self, names):
        orig = getattr(self, '_orig', None)
        if orig is None:
            return True  # new / unknown baseline -> assume changed
        return any(k not in orig or orig[k] != getattr(self, k) for k in names)

    def save(self, *args, **kwargs):
        adding = self._state.adding
        derived = self._apply_derived_fields()

        update_fields = kwargs.get('update_fields')
        if update_fields is not None and derived:
            kwargs['update_fields'] = list(set(update_fields) | set(derived))

        orig = getattr(self, '_orig', None) or {}
        stats_dirty = adding or bool(derived) or self._changed_vs_orig(self._STATS_TRACKED)
        programs = set()
        if stats_dirty:
            programs = {pid for pid in (self.program_id, orig.get('program_id')) if pid}
        self._stats_programs = programs
        self._score_dirty = adding or self._changed_vs_orig(self._SCORE_TRACKED)

        super().save(*args, **kwargs)

        saved = kwargs.get('update_fields')
        self._orig = {
            **orig,
            **{k: getattr(self, k) for k in self._TRACKED
               if saved is None or k in saved or k.removesuffix('_id') in saved},
        }

    def find_potential_duplicates(self, threshold=0.7):
        """
        Find potential duplicate reports based on:
        - Similar title (using simple word overlap)
        - Similar description
        - Same affected URL
        - Same program
        Returns list of (report, similarity_score) tuples
        """
        from django.db.models import Q
        from difflib import SequenceMatcher

        potential_duplicates = []

        # Candidates: same program, or same non-empty affected URL. An empty
        # URL must not match every other URL-less report. Newest first so the
        # 50-row cap below really means "most recent 50".
        match = Q()
        if self.program_id:
            match |= Q(program_id=self.program_id)
        if self.affected_url:
            match |= Q(affected_url=self.affected_url)
        if not match:
            return []

        queryset = BugReport.objects.filter(match).exclude(
            status='duplicate'
        ).exclude(
            duplicate_of__isnull=False
        ).select_related('reporter').order_by('-created_at')

        if self.id:
            queryset = queryset.exclude(id=self.id)

        for report in queryset[:50]:  # Limit to recent 50 for performance
            scores = []

            # Compare titles
            title_sim = SequenceMatcher(None, self.title.lower(), report.title.lower()).ratio()
            scores.append(title_sim)

            # Compare descriptions (first 500 chars for performance)
            desc_sim = SequenceMatcher(
                None,
                (self.description or "")[:500].lower(),
                (report.description or "")[:500].lower()
            ).ratio()
            scores.append(desc_sim)

            # Exact URL match is a strong signal
            if self.affected_url and report.affected_url:
                if self.affected_url.lower() == report.affected_url.lower():
                    scores.append(1.0)  # Boost score for exact URL match

            # Calculate average similarity
            avg_similarity = sum(scores) / len(scores) if scores else 0

            if avg_similarity >= threshold:
                potential_duplicates.append((report, avg_similarity))

        # Sort by similarity score descending
        potential_duplicates.sort(key=lambda x: x[1], reverse=True)
        return potential_duplicates[:5]  # Return top 5

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