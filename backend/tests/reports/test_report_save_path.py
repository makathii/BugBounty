"""
Phase C: BugReport save/signal path (docs/QUERY_PERFORMANCE.md §3.5).

Derived fields are computed in BugReport.save(); program stats and the
leaderboard ledger are only touched when something they depend on changed.
"""
from django.db import connection
from django.test.utils import CaptureQueriesContext

from leaderboard.models import ScoreEvent
from programs.models import Program
from reports.models import BugReport


def _report(user, program, **kw):
    defaults = dict(title="Some report title", description="d", reporter=user,
                    program=program, severity="high")
    defaults.update(kw)
    return BugReport.objects.create(**defaults)


def _count(fn):
    with CaptureQueriesContext(connection) as ctx:
        fn()
    return len(ctx)


def test_derived_fields_set_without_second_write(verified_user, program):
    r = _report(verified_user, program, severity="critical")
    assert r.severity_score == 4
    r.refresh_from_db()
    assert r.severity_score == 4

    r.status = "triaged"
    r.save()
    r.refresh_from_db()
    assert r.time_to_triage is not None and r.time_to_resolution is None

    r.status = "resolved"
    r.save()
    r.refresh_from_db()
    assert r.time_to_resolution is not None


def test_derived_fields_persist_with_update_fields(verified_user, program):
    r = _report(verified_user, program)
    r.status = "triaged"
    r.save(update_fields=["status"])
    r.refresh_from_db()
    assert r.time_to_triage is not None


def test_irrelevant_edit_skips_stats_and_ledger(verified_user, program):
    r = _report(verified_user, program)
    r = BugReport.objects.get(pk=r.pk)  # loaded-from-db baseline
    r.verification_notes = "checked"
    assert _count(r.save) == 1  # just the UPDATE


def test_save_query_budget(verified_user, program):
    r = _report(verified_user, program)
    r = BugReport.objects.get(pk=r.pk)
    r.status = "triaged"
    # UPDATE + stats (ledger aggregate, report aggregate, update) + ledger lookup. Previously 8.
    assert _count(r.save) <= 5


def test_stats_refresh_on_change_and_program_move(verified_user, program):
    other = Program.objects.create(
        company=program.company, name="Other", description="x",
        scope_type="public", status="active",
    )
    r = _report(verified_user, program, status="accepted", severity="low", bonus_points=90)
    program.refresh_from_db()
    assert program.total_reports == 1 and program.total_points == 100

    r = BugReport.objects.get(pk=r.pk)
    r.program = other
    r.save()
    program.refresh_from_db()
    other.refresh_from_db()
    assert program.total_reports == 0, "old program must be refreshed too"
    assert other.total_reports == 1

    r.delete()
    other.refresh_from_db()
    assert other.total_reports == 0


def test_ledger_follows_status_and_ignores_noise(verified_user, program, settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 1, "medium": 3, "high": 7, "critical": 15}
    r = _report(verified_user, program, severity="high")
    assert not ScoreEvent.objects.filter(report=r).exists()

    r = BugReport.objects.get(pk=r.pk)
    r.status = "accepted"
    r.save()
    assert ScoreEvent.objects.get(report=r).points == 7

    r = BugReport.objects.get(pk=r.pk)
    r.severity = "low"
    r.save()
    assert ScoreEvent.objects.get(report=r).points == 1

    r = BugReport.objects.get(pk=r.pk)
    r.status = "duplicate"
    r.save()
    assert not ScoreEvent.objects.filter(report=r).exists()
