"""
Leaderboard scoring services.

All scoring logic lives here so the signals, the management command, and the
API views share one implementation. Nothing else should mutate ScoreEvent
directly.
"""
from datetime import timedelta

from django.db.models import Count, Max, Sum
from django.utils import timezone

from .models import ScoreEvent, severity_points_map, award_statuses


# ---------------------------------------------------------------------------
# Scoring primitives
# ---------------------------------------------------------------------------

def points_for_severity(severity):
    """Points a report of this severity is worth. Unknown severity -> 0."""
    return severity_points_map().get((severity or "").lower(), 0)


def is_awardable(report):
    """
    A report earns points only when it is in an awardable status AND is not
    itself flagged as a duplicate. Duplicates never score, even if their status
    field still reads e.g. 'accepted'.
    """
    if getattr(report, "duplicate_of_id", None):
        return False
    if report.status == "duplicate":
        return False
    return report.status in award_statuses()


def sync_report_score(report):
    """
    Reconcile a report's ScoreEvent with its current state. Idempotent.

    - Awardable    -> create the ledger row, or update points/severity/program
                      if they drifted. ``awarded_at`` is set once and preserved.
    - Not awardable -> remove any existing ledger row (points revoked).

    Returns the ScoreEvent if one exists afterwards, else None.
    """
    if not report.reporter_id:
        return None

    existing = ScoreEvent.objects.filter(report=report).first()

    if not is_awardable(report):
        if existing:
            existing.delete()
        return None

    points = points_for_severity(report.severity)

    if existing is None:
        return ScoreEvent.objects.create(
            researcher_id=report.reporter_id,
            report=report,
            program_id=report.program_id,
            points=points,
            severity=report.severity or "",
            awarded_at=timezone.now(),
        )

    # Update in place if anything relevant changed; keep awarded_at stable so
    # the report stays in the same weekly/monthly bucket it was first awarded.
    changed = []
    if existing.points != points:
        existing.points = points
        changed.append("points")
    if existing.severity != (report.severity or ""):
        existing.severity = report.severity or ""
        changed.append("severity")
    if existing.researcher_id != report.reporter_id:
        existing.researcher_id = report.reporter_id
        changed.append("researcher")
    if existing.program_id != report.program_id:
        existing.program_id = report.program_id
        changed.append("program")
    if changed:
        existing.save(update_fields=changed + ["updated_at"])
    return existing


# ---------------------------------------------------------------------------
# Time windows
# ---------------------------------------------------------------------------

VALID_PERIODS = ("all", "monthly", "weekly")


def period_start(period, now=None):
    """
    Return the lower-bound datetime for a period, or None for 'all'.
    'weekly' = last 7 days, 'monthly' = last 30 days (rolling windows).
    """
    now = now or timezone.now()
    if period == "weekly":
        return now - timedelta(days=7)
    if period == "monthly":
        return now - timedelta(days=30)
    return None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _base_queryset(period="all", program=None, now=None):
    qs = ScoreEvent.objects.all()
    if program is not None:
        program_id = getattr(program, "pk", program)
        qs = qs.filter(program_id=program_id)
    start = period_start(period, now=now)
    if start is not None:
        qs = qs.filter(awarded_at__gte=start)
    return qs


def leaderboard_rows(period="all", program=None, now=None):
    """
    Aggregate the ledger into per-researcher rows, ranked by total points
    (ties broken by report_count, then most recent activity). Returns a list of
    dicts: researcher_id, username, total_points, report_count, last_awarded_at.
    No pagination here — callers slice the result.
    """
    qs = _base_queryset(period=period, program=program, now=now)
    rows = (
        qs.values("researcher_id", "researcher__username")
        .annotate(
            total_points=Sum("points"),
            report_count=Count("id"),
            last_awarded_at=Max("awarded_at"),
        )
        .order_by("-total_points", "-report_count", "-last_awarded_at")
    )

    result = []
    for rank, row in enumerate(rows, start=1):
        result.append({
            "rank": rank,
            "researcher_id": row["researcher_id"],
            "username": row["researcher__username"],
            "total_points": row["total_points"] or 0,
            "report_count": row["report_count"],
            "last_awarded_at": row["last_awarded_at"],
        })
    return result


def rank_for(user, period="all", program=None, now=None):
    """
    Return a single researcher's standing as a row dict (same shape as
    ``leaderboard_rows`` entries), or None if they have no points in the window.
    Computed from the full ordered list so the rank is exact.
    """
    user_id = getattr(user, "pk", user)
    for row in leaderboard_rows(period=period, program=program, now=now):
        if row["researcher_id"] == user_id:
            return row
    return None


def recompute_all():
    """
    Rebuild the entire ledger from live report data. Wipes ScoreEvent and
    re-derives it from every BugReport. Safe to run repeatedly; used by the
    ``recompute_leaderboard`` management command and after config changes.
    Returns the number of events created.
    """
    from reports.models import BugReport

    ScoreEvent.objects.all().delete()
    created = 0
    for report in BugReport.objects.all().iterator():
        if sync_report_score(report) is not None:
            created += 1
    return created
