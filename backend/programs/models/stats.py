from django.db import models
from django.utils import timezone

from .program import Program


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
