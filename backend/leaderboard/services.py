"""
Leaderboard scoring services.

All scoring logic lives here so the signals, the management command, and the
API views share one implementation. Nothing else should mutate ScoreEvent
directly.
"""
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F, Max, Q, Sum, Window
from django.db.models.functions import RowNumber
from django.utils import timezone

from .models import ScoreEvent, severity_points_map, award_statuses


# ---------------------------------------------------------------------------
# Result cache
# ---------------------------------------------------------------------------
# Rankings are cached briefly. Every ledger mutation (ScoreEvent save/delete,
# including cascades from deleting a report; see leaderboard.signals) bumps a version number
# that is part of every cache key, so writes invalidate all cached pages at
# once. Rolling windows move with the clock, so the TTL bounds their staleness.
# NOTE: with the default per-process LocMemCache, a version bump is only seen by
# the process that made it; other workers serve stale pages for at most the TTL.
# Configure a shared cache (Redis/Memcached) to get immediate invalidation.

_VERSION_KEY = "leaderboard:version"


def cache_ttl():
    return int(getattr(settings, "LEADERBOARD_CACHE_TTL", 30))


def _cache_version():
    return cache.get(_VERSION_KEY, 0)


def bump_cache_version():
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:  # key missing
        cache.set(_VERSION_KEY, 1, None)


def _cached(key_parts, compute, now=None):
    """Return ``compute()``, cached by key. Skipped when ``now`` is pinned or TTL is 0."""
    ttl = cache_ttl()
    if ttl <= 0 or now is not None:
        return compute()
    key = "leaderboard:" + ":".join(str(p) for p in (_cache_version(), *key_parts))
    hit = cache.get(key)
    if hit is not None:
        return hit
    value = compute()
    cache.set(key, value, ttl)
    return value


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
        event = ScoreEvent.objects.create(
            researcher_id=report.reporter_id,
            report=report,
            program_id=report.program_id,
            points=points,
            severity=report.severity or "",
            awarded_at=timezone.now(),
        )
        return event

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


_ROW_FIELDS = ("rank", "researcher_id", "researcher__username",
               "total_points", "report_count", "last_awarded_at")


def _ranked_queryset(period="all", program=None, now=None):
    """
    Per-researcher aggregate with the rank computed in SQL (ROW_NUMBER over the
    aggregate). Order: points desc, report_count desc, most recent activity,
    then researcher id so the order is fully deterministic.
    """
    qs = _base_queryset(period=period, program=program, now=now)
    return (
        qs.values("researcher_id", "researcher__username")
        .annotate(
            total_points=Sum("points"),
            report_count=Count("id"),
            last_awarded_at=Max("awarded_at"),
        )
        .annotate(
            rank=Window(
                expression=RowNumber(),
                order_by=[
                    F("total_points").desc(),
                    F("report_count").desc(),
                    F("last_awarded_at").desc(),
                    F("researcher_id").asc(),
                ],
            )
        )
        .order_by("rank")
    )


def _row_dict(row):
    return {
        "rank": row["rank"],
        "researcher_id": row["researcher_id"],
        "username": row["researcher__username"],
        "total_points": row["total_points"] or 0,
        "report_count": row["report_count"],
        "last_awarded_at": row["last_awarded_at"],
    }


def leaderboard_page(period="all", program=None, limit=None, offset=0, now=None):
    """
    One page of the ranking plus the total number of ranked researchers:
    ``(rows, total)``. Paging happens in the database (LIMIT/OFFSET over the
    windowed query) so cost does not depend on how many researchers exist
    beyond the page. ``limit=None`` returns everything from ``offset``.
    """
    program_id = getattr(program, "pk", program)

    def compute():
        base = _base_queryset(period=period, program=program, now=now)
        total = base.values("researcher_id").distinct().count()
        qs = _ranked_queryset(period=period, program=program, now=now)
        end = None if limit is None else offset + limit
        rows = [_row_dict(r) for r in qs[offset:end]]
        return rows, total

    return _cached(("page", period, program_id, limit, offset), compute, now=now)


def leaderboard_rows(period="all", program=None, now=None):
    """
    The complete ranking as a list of dicts: rank, researcher_id, username,
    total_points, report_count, last_awarded_at. Prefer ``leaderboard_page``
    for anything user-facing.
    """
    return leaderboard_page(period=period, program=program, now=now)[0]


def rank_for(user, period="all", program=None, now=None):
    """
    Return a single researcher's standing as a row dict (same shape as
    ``leaderboard_rows`` entries), or None if they have no points in the window.
    Two small aggregate queries; nothing is materialized in Python.
    """
    user_id = getattr(user, "pk", user)
    program_id = getattr(program, "pk", program)

    def compute():
        base = _base_queryset(period=period, program=program, now=now)
        grouped = base.values("researcher_id").annotate(
            tp=Sum("points"), rc=Count("id"), la=Max("awarded_at")
        )
        mine = (
            base.filter(researcher_id=user_id)
            .values("researcher_id", "researcher__username")
            .annotate(tp=Sum("points"), rc=Count("id"), la=Max("awarded_at"))
            .order_by("researcher_id")
            .first()
        )
        if mine is None:
            return None
        tp, rc, la = mine["tp"], mine["rc"], mine["la"]
        # Rank = 1 + number of researchers ordered strictly before this one
        # (same ordering as _ranked_queryset). A window-function filter would
        # be computed *after* narrowing to this researcher, giving rank 1.
        ahead = grouped.order_by().filter(
            Q(tp__gt=tp)
            | Q(tp=tp, rc__gt=rc)
            | Q(tp=tp, rc=rc, la__gt=la)
            | Q(tp=tp, rc=rc, la=la, researcher_id__lt=user_id)
        ).count()
        return {
            "rank": ahead + 1,
            "researcher_id": user_id,
            "username": mine["researcher__username"],
            "total_points": tp or 0,
            "report_count": rc,
            "last_awarded_at": la,
        }

    result = _cached(("rank", period, program_id, user_id), compute, now=now)
    return result


def recompute_all():
    """
    Rebuild the entire ledger from live report data. Wipes ScoreEvent and
    re-derives it from every BugReport inside one transaction (readers never
    see an empty ledger), using bulk inserts. Safe to run repeatedly; used by
    the ``recompute_leaderboard`` management command and after config changes.
    Returns the number of events created.
    """
    from reports.models import BugReport

    now = timezone.now()
    events = []
    reports = BugReport.objects.only(
        "id", "reporter_id", "program_id", "severity", "status", "duplicate_of_id"
    )
    for report in reports.iterator(chunk_size=2000):
        if not report.reporter_id or not is_awardable(report):
            continue
        events.append(ScoreEvent(
            researcher_id=report.reporter_id,
            report_id=report.pk,
            program_id=report.program_id,
            points=points_for_severity(report.severity),
            severity=report.severity or "",
            awarded_at=now,
        ))

    with transaction.atomic():
        ScoreEvent.objects.all().delete()
        ScoreEvent.objects.bulk_create(events, batch_size=1000)
    bump_cache_version()
    return len(events)
