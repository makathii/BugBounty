from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Scoring configuration
# ---------------------------------------------------------------------------
# Points awarded per accepted/resolved report, weighted by severity. Tunable
# via settings so the platform can rebalance the economy without a code change.
# Defaults make critical findings worth dramatically more than lows, which is
# the norm for bug-bounty reputation systems.
DEFAULT_SEVERITY_POINTS = {
    "low": 1,
    "medium": 3,
    "high": 7,
    "critical": 15,
}

# A report only earns points once it reaches one of these statuses (and is not
# itself a duplicate). See leaderboard.services.is_awardable.
DEFAULT_AWARD_STATUSES = ("accepted", "resolved")


def severity_points_map():
    """Return the severity -> points map, overridable via settings."""
    return getattr(settings, "LEADERBOARD_SEVERITY_POINTS", DEFAULT_SEVERITY_POINTS)


def award_statuses():
    """Return the tuple of report statuses that earn points."""
    return tuple(getattr(settings, "LEADERBOARD_AWARD_STATUSES", DEFAULT_AWARD_STATUSES))


# ---------------------------------------------------------------------------
# ScoreEvent — the points ledger
# ---------------------------------------------------------------------------

class ScoreEvent(models.Model):
    """
    A single points-earning event, tied one-to-one to a BugReport.

    This is the *source of truth* for the leaderboard. Rankings are computed by
    aggregating ScoreEvent rows, never by mutating a running total on the user,
    which keeps the score auditable and recomputable (see the
    ``recompute_leaderboard`` management command).

    Rows are created / updated / deleted automatically by
    ``leaderboard.signals`` as a report's status and severity change.
    """

    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="score_events",
    )
    # One ledger row per report. Deleting the report removes its points.
    report = models.OneToOneField(
        "reports.BugReport",
        on_delete=models.CASCADE,
        related_name="score_event",
    )
    # Denormalised from the report so per-program leaderboards stay a single
    # indexed query (no join back through reports for every aggregation).
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="score_events",
        null=True,
        blank=True,
    )

    points = models.PositiveIntegerField(default=0)
    # Snapshot of the severity that produced ``points`` at award time, so the
    # ledger explains itself even if config or the report later changes.
    severity = models.CharField(max_length=10, blank=True, default="")

    # When the report first became awardable. Drives the weekly / monthly
    # windows. Set once on creation and preserved across later updates.
    awarded_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-awarded_at"]
        indexes = [
            models.Index(fields=["researcher", "awarded_at"]),
            models.Index(fields=["program", "awarded_at"]),
        ]

    def __str__(self):
        return f"{self.researcher} +{self.points} (report #{self.report_id})"
