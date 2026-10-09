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
