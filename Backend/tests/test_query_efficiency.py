"""
Regression tests for the query-count / correctness fixes from
docs/QUERY_PERFORMANCE.md (phase A).
"""
import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from core.roles import get_roles
from programs.models import Program, ProgramFavorite, Scope
from reports.models import BugReport


def _make_reports(reporter, program, n):
    for i in range(n):
        BugReport.objects.create(
            title=f"Report number {i:03d}", description="d", reporter=reporter,
            program=program, assigned_to=reporter,
        )


def _queries(client, url):
    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(url)
    assert resp.status_code == 200, resp.content
    return len(ctx), resp


def test_report_list_query_count_is_constant(triager_user, verified_user, program):
    client = APIClient()
    client.force_authenticate(triager_user)

    _make_reports(verified_user, program, 2)
    small, _ = _queries(client, "/api/reports/")
    _make_reports(verified_user, program, 20)
    large, resp = _queries(client, "/api/reports/")

    assert large == small, "report list issues per-row queries (N+1)"
    results = resp.data["results"] if isinstance(resp.data, dict) else resp.data
    assert results[0]["program_name"] == program.name


def test_triage_dashboard_counts_use_one_aggregate(triager_user, verified_user, program):
    client = APIClient()
    client.force_authenticate(triager_user)
    _make_reports(verified_user, program, 3)
    BugReport.objects.filter(title__endswith="001").update(status="triaged")

    n, resp = _queries(client, "/api/reports/triage_dashboard/")
    assert resp.data["counts"] == {
        "total": 3, "open": 2, "triaged": 1, "accepted": 0, "rejected": 0,
        "assigned_to_me": 0, "unassigned": 0,
    }
    # 1 auth-group lookup + 1 aggregate + 1 recent list (+ small constant for session/user)
    assert n <= 5


def test_roles_are_cached_per_request(triager_user):
    class Req:
        user = triager_user

    req = Req()
    with CaptureQueriesContext(connection) as ctx:
        assert "Triager" in get_roles(req)
        get_roles(req)
        get_roles(req)
    assert len(ctx) == 1


def test_roles_not_stale_across_requests(db, verified_user, triager_group):
    class Req:
        user = verified_user

    assert "Triager" not in get_roles(Req())
    verified_user.groups.add(triager_group)
    assert "Triager" in get_roles(Req())  # new request, same user object


def test_program_list_favorites_count_is_annotated(verified_user, second_verified_user, program):
    client = APIClient()
    client.force_authenticate(verified_user)
    ProgramFavorite.objects.create(program=program, researcher=second_verified_user)
    ProgramFavorite.objects.create(program=program, researcher=verified_user)

    base, resp = _queries(client, "/api/programs/researcher/")
    rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
    assert [r["favorites_count"] for r in rows if r["id"] == program.id] == [2]

    for i in range(5):
        p = Program.objects.create(
            company=program.company, name=f"Extra {i}", description="x",
            scope_type="public", status="active",
        )
        Scope.objects.create(program=p, target="a.example.com", target_type="domain")
    more, _ = _queries(client, "/api/programs/researcher/")
    assert more == base


def test_duplicate_detection_ignores_empty_url_matches(verified_user, second_verified_user, program):
    other = Program.objects.create(
        company=program.company, name="Other", description="x",
        scope_type="public", status="active",
    )
    BugReport.objects.create(
        title="Stored XSS in profile page", description="payload in bio field",
        reporter=second_verified_user, program=other, affected_url="",
    )
    probe = BugReport(
        title="Stored XSS in profile page", description="payload in bio field",
        reporter=verified_user, program=program, affected_url="",
    )
    # Different program + both URLs empty: must NOT be treated as a candidate.
    assert probe.find_potential_duplicates() == []


def test_duplicate_detection_prefers_most_recent(verified_user, program):
    for i in range(60):
        BugReport.objects.create(
            title=f"filler {i}", description="zzz", reporter=verified_user, program=program,
        )
    newest = BugReport.objects.create(
        title="Open redirect on login", description="next param not validated",
        reporter=verified_user, program=program,
    )
    probe = BugReport(
        title="Open redirect on login", description="next param not validated",
        reporter=verified_user, program=program,
    )
    found = probe.find_potential_duplicates()
    assert found and found[0][0].id == newest.id
