"""
Tests for the leaderboard app.

Covers:
  - Ledger sync: points awarded on accept/resolve, revoked otherwise
  - Severity weighting and the duplicate exclusion rule
  - Aggregation: ordering, ranks, per-program scope, time windows
  - API: list / me / retrieve endpoints, params validation, auth
  - recompute_leaderboard rebuild
"""
import pytest
from datetime import timedelta

from django.utils import timezone

from reports.models import BugReport
from leaderboard.models import ScoreEvent
from leaderboard import services


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def small_point_table(settings):
    """These tests are about ledger mechanics, not tuning: pin a simple point table."""
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 1, "medium": 3, "high": 7, "critical": 15}


def make_report(reporter, program, severity="medium", status="accepted"):
    return BugReport.objects.create(
        title=f"{severity} issue by {reporter.username}",
        description="A sufficiently long description of the vulnerability for testing.",
        severity=severity,
        status=status,
        reporter=reporter,
        program=program,
    )


# ---------------------------------------------------------------------------
# Ledger sync
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLedgerSync:
    def test_accepted_report_awards_points(self, verified_user, program):
        make_report(verified_user, program, severity="high", status="accepted")
        event = ScoreEvent.objects.get(researcher=verified_user)
        assert event.points == 7  # high
        assert event.severity == "high"
        assert event.program_id == program.id

    def test_resolved_report_awards_points(self, verified_user, program):
        make_report(verified_user, program, severity="critical", status="resolved")
        assert ScoreEvent.objects.get(researcher=verified_user).points == 15

    @pytest.mark.parametrize("severity,expected", [
        ("low", 1), ("medium", 3), ("high", 7), ("critical", 15),
    ])
    def test_severity_weighting(self, verified_user, program, severity, expected):
        make_report(verified_user, program, severity=severity, status="accepted")
        assert ScoreEvent.objects.get(researcher=verified_user).points == expected

    def test_open_report_earns_nothing(self, verified_user, program):
        make_report(verified_user, program, status="open")
        assert ScoreEvent.objects.count() == 0

    def test_triaged_report_earns_nothing(self, verified_user, program):
        make_report(verified_user, program, status="triaged")
        assert ScoreEvent.objects.count() == 0

    def test_points_revoked_when_status_leaves_awardable(self, verified_user, program):
        report = make_report(verified_user, program, status="accepted")
        assert ScoreEvent.objects.count() == 1
        report.status = "rejected"
        report.save()
        assert ScoreEvent.objects.count() == 0

    def test_points_update_when_severity_changes(self, verified_user, program):
        report = make_report(verified_user, program, severity="low", status="accepted")
        assert ScoreEvent.objects.get(report=report).points == 1
        report.severity = "critical"
        report.save()
        assert ScoreEvent.objects.get(report=report).points == 15

    def test_duplicate_report_earns_nothing(self, verified_user, second_verified_user, program):
        original = make_report(second_verified_user, program, status="accepted")
        dup = make_report(verified_user, program, status="accepted")
        dup.duplicate_of = original
        dup.status = "duplicate"
        dup.save()
        assert not ScoreEvent.objects.filter(researcher=verified_user).exists()

    def test_deleting_report_removes_event(self, verified_user, program):
        report = make_report(verified_user, program, status="accepted")
        assert ScoreEvent.objects.count() == 1
        report.delete()
        assert ScoreEvent.objects.count() == 0

    def test_awarded_at_is_stable_across_updates(self, verified_user, program):
        report = make_report(verified_user, program, severity="low", status="accepted")
        original = ScoreEvent.objects.get(report=report).awarded_at
        report.severity = "high"
        report.save()
        assert ScoreEvent.objects.get(report=report).awarded_at == original


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAggregation:
    def test_ranking_order_and_ranks(self, verified_user, second_verified_user, program):
        # verified_user: one critical (15); second: one low (1)
        make_report(verified_user, program, severity="critical", status="accepted")
        make_report(second_verified_user, program, severity="low", status="accepted")

        rows = services.leaderboard_rows()
        assert rows[0]["researcher_id"] == verified_user.id
        assert rows[0]["rank"] == 1
        assert rows[0]["total_points"] == 15
        assert rows[1]["researcher_id"] == second_verified_user.id
        assert rows[1]["rank"] == 2

    def test_points_sum_across_reports(self, verified_user, program):
        make_report(verified_user, program, severity="high", status="accepted")     # 7
        make_report(verified_user, program, severity="medium", status="accepted")   # 3
        row = services.rank_for(verified_user)
        assert row["total_points"] == 10
        assert row["report_count"] == 2

    def test_per_program_scope(self, verified_user, program, active_program):
        make_report(verified_user, program, severity="high", status="accepted")          # prog A: 7
        make_report(verified_user, active_program, severity="low", status="accepted")    # prog B: 1
        assert services.rank_for(verified_user, program=program)["total_points"] == 7
        assert services.rank_for(verified_user, program=active_program)["total_points"] == 1
        assert services.rank_for(verified_user)["total_points"] == 8

    def test_weekly_window_excludes_old_events(self, verified_user, program):
        make_report(verified_user, program, severity="high", status="accepted")
        # Backdate the event beyond the 7-day window.
        ScoreEvent.objects.update(awarded_at=timezone.now() - timedelta(days=10))
        assert services.rank_for(verified_user, period="weekly") is None
        # Still counts monthly (within 30 days) and all-time.
        assert services.rank_for(verified_user, period="monthly")["total_points"] == 7
        assert services.rank_for(verified_user, period="all")["total_points"] == 7

    def test_monthly_window_excludes_very_old_events(self, verified_user, program):
        make_report(verified_user, program, severity="high", status="accepted")
        ScoreEvent.objects.update(awarded_at=timezone.now() - timedelta(days=40))
        assert services.rank_for(verified_user, period="monthly") is None
        assert services.rank_for(verified_user, period="all")["total_points"] == 7


# ---------------------------------------------------------------------------
# recompute
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRecompute:
    def test_recompute_rebuilds_ledger(self, verified_user, program):
        make_report(verified_user, program, severity="high", status="accepted")
        ScoreEvent.objects.all().delete()
        assert ScoreEvent.objects.count() == 0
        created = services.recompute_all()
        assert created == 1
        assert ScoreEvent.objects.get(researcher=verified_user).points == 7


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLeaderboardAPI:
    def test_list_requires_auth(self, api_client):
        assert api_client.get("/api/leaderboard/").status_code == 401

    def test_me_requires_auth(self, api_client):
        assert api_client.get("/api/leaderboard/me/").status_code == 401

    def test_list_returns_ranked_results(self, api_client, verified_user, second_verified_user, program):
        make_report(verified_user, program, severity="critical", status="accepted")
        make_report(second_verified_user, program, severity="low", status="accepted")
        api_client.force_authenticate(user=verified_user)

        resp = api_client.get("/api/leaderboard/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert body["results"][0]["username"] == verified_user.username
        assert body["results"][0]["rank"] == 1
        assert body["results"][0]["total_points"] == 15

    def test_list_program_filter(self, api_client, verified_user, program, active_program):
        make_report(verified_user, program, severity="high", status="accepted")
        make_report(verified_user, active_program, severity="low", status="accepted")
        api_client.force_authenticate(user=verified_user)

        resp = api_client.get(f"/api/leaderboard/?program={program.id}")
        assert resp.status_code == 200
        assert resp.json()["results"][0]["total_points"] == 7

    def test_list_invalid_period_is_400(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        assert api_client.get("/api/leaderboard/?period=yearly").status_code == 400

    def test_me_returns_own_rank(self, api_client, verified_user, program):
        make_report(verified_user, program, severity="medium", status="accepted")
        api_client.force_authenticate(user=verified_user)

        resp = api_client.get("/api/leaderboard/me/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ranked"] is True
        assert body["result"]["total_points"] == 3

    def test_me_unranked_when_no_points(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get("/api/leaderboard/me/")
        assert resp.status_code == 200
        assert resp.json()["ranked"] is False

    def test_retrieve_researcher_standing(self, api_client, verified_user, second_verified_user, program):
        make_report(verified_user, program, severity="high", status="accepted")
        api_client.force_authenticate(user=second_verified_user)

        resp = api_client.get(f"/api/leaderboard/{verified_user.id}/")
        assert resp.status_code == 200
        assert resp.json()["result"]["total_points"] == 7

    def test_retrieve_unranked_researcher_is_404(self, api_client, verified_user, second_verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(f"/api/leaderboard/{second_verified_user.id}/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Phase D: SQL ranking, DB paging, caching, atomic recompute
# ---------------------------------------------------------------------------

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext


def _ledger_user(name):
    return User.objects.create_user(username=name, password="x")


@pytest.mark.django_db
class TestSqlRanking:
    def _seed(self, program, n=12):
        users = [_ledger_user(f"u{i:02d}") for i in range(n)]
        for i, u in enumerate(users):
            for _ in range(1 + i % 3):
                make_report(u, program, severity="medium", status="accepted")
        return users

    def test_paging_is_consistent_with_full_ranking(self, program):
        self._seed(program)
        full = services.leaderboard_rows()
        assert [r["rank"] for r in full] == list(range(1, len(full) + 1))
        pages = []
        for off in range(0, len(full), 5):
            rows, total = services.leaderboard_page(limit=5, offset=off)
            assert total == len(full)
            pages.extend(rows)
        assert pages == full

    def test_ties_are_deterministic(self, program):
        users = [_ledger_user(f"t{i}") for i in range(4)]
        for u in users:
            make_report(u, program, severity="low", status="accepted")
        # identical points/count; last_awarded_at differs only by creation order
        a = [r["researcher_id"] for r in services.leaderboard_rows()]
        cache.clear()
        b = [r["researcher_id"] for r in services.leaderboard_rows()]
        assert a == b and len(set(a)) == 4

    def test_rank_for_matches_listing_and_is_one_row(self, program):
        users = self._seed(program)
        full = {r["researcher_id"]: r for r in services.leaderboard_rows()}
        cache.clear()
        target = users[7]
        with CaptureQueriesContext(connection) as ctx:
            row = services.rank_for(target)
        assert row == full[target.id]
        assert len(ctx) <= 2

    def test_page_query_count_independent_of_size(self, program):
        self._seed(program, n=3)
        cache.clear()
        with CaptureQueriesContext(connection) as small:
            services.leaderboard_page(limit=5)
        self._seed_more = [_ledger_user(f"x{i}") for i in range(30)]
        for u in self._seed_more:
            make_report(u, program, status="accepted")
        cache.clear()
        with CaptureQueriesContext(connection) as large:
            services.leaderboard_page(limit=5)
        assert len(large) == len(small) <= 2


@pytest.mark.django_db
class TestLeaderboardCache:
    def test_second_call_hits_cache(self, verified_user, program):
        make_report(verified_user, program, status="accepted")
        services.leaderboard_page()
        with CaptureQueriesContext(connection) as ctx:
            services.leaderboard_page()
        assert len(ctx) == 0

    def test_invalidated_by_ledger_changes(self, verified_user, second_verified_user, program):
        report = make_report(verified_user, program, severity="low", status="accepted")
        assert services.rank_for(verified_user)["total_points"] == 1
        report.severity = "critical"
        report.save()
        assert services.rank_for(verified_user)["total_points"] == 15

        make_report(second_verified_user, program, severity="medium", status="accepted")
        assert services.leaderboard_page()[1] == 2

        report.delete()  # cascade removes the ScoreEvent
        assert services.leaderboard_page()[1] == 1
        assert services.rank_for(verified_user) is None

    def test_ttl_zero_disables_cache(self, settings, verified_user, program):
        settings.LEADERBOARD_CACHE_TTL = 0
        make_report(verified_user, program, status="accepted")
        services.leaderboard_page()
        with CaptureQueriesContext(connection) as ctx:
            services.leaderboard_page()
        assert len(ctx) > 0


@pytest.mark.django_db
class TestRecomputeAtomic:
    def test_recompute_matches_incremental_ledger(self, verified_user, second_verified_user, program):
        make_report(verified_user, program, severity="high", status="accepted")
        make_report(second_verified_user, program, severity="low", status="resolved")
        make_report(verified_user, program, severity="critical", status="open")
        before = sorted(ScoreEvent.objects.values_list("researcher_id", "report_id", "points", "severity"))
        assert services.recompute_all() == 2
        after = sorted(ScoreEvent.objects.values_list("researcher_id", "report_id", "points", "severity"))
        assert before == after

    def test_recompute_uses_bulk_insert(self, verified_user, program):
        for _ in range(10):
            make_report(verified_user, program, status="accepted")
        with CaptureQueriesContext(connection) as ctx:
            services.recompute_all()
        inserts = [q for q in ctx.captured_queries if q["sql"].lstrip().upper().startswith("INSERT")]
        assert len(inserts) == 1

    def test_recompute_failure_rolls_back(self, verified_user, program, monkeypatch):
        make_report(verified_user, program, status="accepted")
        def boom(*a, **k):
            raise RuntimeError("insert failed")
        monkeypatch.setattr(ScoreEvent.objects.__class__, "bulk_create", boom)
        with pytest.raises(RuntimeError):
            services.recompute_all()
        assert ScoreEvent.objects.count() == 1  # old ledger intact


# ---------------------------------------------------------------------------
# Points economy
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPointsEconomy:
    def test_default_point_table(self, settings, verified_user, program):
        del settings.LEADERBOARD_SEVERITY_POINTS  # fall back to the shipped economy
        from leaderboard.models import DEFAULT_SEVERITY_POINTS
        assert DEFAULT_SEVERITY_POINTS == {"low": 10, "medium": 30, "high": 70, "critical": 150}
        report = make_report(verified_user, program, severity="high")
        assert ScoreEvent.objects.get(report=report).points == 70

    def test_bonus_points_add_to_the_award(self, verified_user, program):
        report = make_report(verified_user, program, severity="high", status="triaged")
        assert not ScoreEvent.objects.filter(report=report).exists()
        report.status = "accepted"
        report.bonus_points = 20
        report.save()
        assert ScoreEvent.objects.get(report=report).points == 27  # 7 + 20
        assert report.points_awarded == 27

    def test_changing_the_bonus_updates_the_ledger(self, verified_user, program):
        report = make_report(verified_user, program, severity="low")
        report.bonus_points = 5
        report.save()
        assert ScoreEvent.objects.get(report=report).points == 6
        report.bonus_points = 0
        report.save()
        assert ScoreEvent.objects.get(report=report).points == 1

    def test_recompute_includes_bonus(self, verified_user, program):
        report = make_report(verified_user, program, severity="medium")
        BugReport.objects.filter(pk=report.pk).update(bonus_points=10)
        services.recompute_all()
        assert ScoreEvent.objects.get(report=report).points == 13

    def test_points_awarded_is_zero_until_accepted(self, verified_user, program):
        report = make_report(verified_user, program, status="open")
        assert BugReport.objects.get(pk=report.pk).points_awarded == 0
