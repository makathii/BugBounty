"""
Tests for the full report workflow.

Covers endpoints that had no previous tests:
  - Comment submission and access control
  - Triage actions: accept, reject, reopen, assign_to_me
  - Activity log retrieval
  - Stats and my_submissions aggregations
  - Submit-for-review flow
  - Triage dashboard
  - Report CRUD (retrieve, update, delete) with permission checks
  - Unauthenticated access returns 401 on all report endpoints
"""
import pytest
from django.contrib.auth.models import User
from reports.models import BugReport, Comment, ActivityLog


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUnauthenticatedAccess:
    """Every report endpoint must return 401 for unauthenticated callers."""

    def test_list_reports_requires_auth(self, api_client):
        assert api_client.get("/api/reports/").status_code == 401

    def test_create_report_requires_auth(self, api_client, report_payload):
        assert api_client.post("/api/reports/", report_payload, format="json").status_code == 401

    def test_retrieve_report_requires_auth(self, api_client, own_report):
        assert api_client.get(f"/api/reports/{own_report.id}/").status_code == 401

    def test_triage_dashboard_requires_auth(self, api_client):
        assert api_client.get("/api/reports/triage_dashboard/").status_code == 401

    def test_my_submissions_requires_auth(self, api_client):
        assert api_client.get("/api/reports/my_submissions/").status_code == 401

    def test_stats_requires_auth(self, api_client):
        assert api_client.get("/api/reports/stats/").status_code == 401

    def test_check_duplicates_requires_auth(self, api_client):
        assert api_client.post("/api/reports/check_duplicates/", {}, format="json").status_code == 401


# ---------------------------------------------------------------------------
# Report retrieve / update / delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportCRUD:
    def test_owner_can_retrieve_own_report(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(f"/api/reports/{own_report.id}/")
        assert resp.status_code == 200
        assert resp.data["id"] == own_report.id

    def test_researcher_cannot_retrieve_others_report(self, api_client, verified_user, other_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(f"/api/reports/{other_report.id}/")
        # Queryset-scoped access: DRF returns 404 (not found in user's queryset) rather
        # than 403 (forbidden) — both are correct security behavior (hides existence).
        assert resp.status_code in (403, 404)

    def test_triager_can_retrieve_any_report(self, api_client, triager_user, other_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.get(f"/api/reports/{other_report.id}/")
        assert resp.status_code == 200

    def test_owner_can_update_own_open_report(self, api_client, verified_user, own_report, monkeypatch):
        monkeypatch.setattr("reports.tasks.send_mail", lambda *a, **k: 1)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(
            f"/api/reports/{own_report.id}/",
            {"title": "Updated title for the report"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["title"] == "Updated title for the report"

    def test_researcher_cannot_update_others_report(self, api_client, verified_user, other_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(
            f"/api/reports/{other_report.id}/",
            {"title": "Hijacked title"},
            format="json",
        )
        # Queryset-scoped: 404 is the expected security behavior (report not in user's queryset).
        assert resp.status_code in (403, 404)

    def test_owner_can_delete_own_report(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.delete(f"/api/reports/{own_report.id}/")
        assert resp.status_code == 204
        assert not BugReport.objects.filter(id=own_report.id).exists()

    def test_researcher_cannot_delete_others_report(self, api_client, verified_user, other_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.delete(f"/api/reports/{other_report.id}/")
        # Queryset-scoped: 404 is the expected security behavior (report not in user's queryset).
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComments:
    def test_researcher_can_comment_on_own_report(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"/api/reports/{own_report.id}/comment/",
            {"text": "Here is more detail about the reproduction steps."},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["text"] == "Here is more detail about the reproduction steps."

    def test_comment_records_author(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        api_client.post(
            f"/api/reports/{own_report.id}/comment/",
            {"text": "My comment"},
            format="json",
        )
        comment = Comment.objects.get(report=own_report)
        assert comment.author == verified_user

    def test_triager_can_comment_on_any_report(self, api_client, triager_user, other_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(
            f"/api/reports/{other_report.id}/comment/",
            {"text": "Triager note on this report."},
            format="json",
        )
        assert resp.status_code == 201

    def test_comment_requires_text(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"/api/reports/{own_report.id}/comment/",
            {"text": ""},
            format="json",
        )
        assert resp.status_code == 400

    def test_triager_comments_list_includes_all_reports(self, api_client, triager_user, own_report, other_report):
        """Triagers can see comments on all reports via /api/comments/."""
        Comment.objects.create(report=own_report, author=own_report.reporter, text="Comment A")
        Comment.objects.create(report=other_report, author=other_report.reporter, text="Comment B")
        api_client.force_authenticate(user=triager_user)
        resp = api_client.get("/api/comments/")
        assert resp.status_code == 200
        texts = [c["text"] for c in resp.data]
        assert "Comment A" in texts
        assert "Comment B" in texts

    def test_researcher_comment_list_scoped_to_own_reports(self, api_client, verified_user, own_report, other_report):
        """Researchers should only see comments on their own reports."""
        Comment.objects.create(report=own_report, author=verified_user, text="Own comment")
        Comment.objects.create(report=other_report, author=other_report.reporter, text="Other comment")
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get("/api/comments/")
        assert resp.status_code == 200
        texts = [c["text"] for c in resp.data]
        assert "Own comment" in texts
        assert "Other comment" not in texts

    def test_comment_strips_script_tags(self, api_client, verified_user, own_report):
        """Stored XSS prevention — <script> tags must be stripped before saving.

        bleach strip=True removes tags but keeps inner text as inert plain text,
        so "alert('xss')" may survive as text — that is fine because text alone
        does not execute.  What matters is that the <script> wrapper is gone.
        """
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"/api/reports/{own_report.id}/comment/",
            {"text": "<script>alert('xss')</script>Found a bug."},
            format="json",
        )
        assert resp.status_code == 201
        assert "<script>" not in resp.data["text"]
        assert "</script>" not in resp.data["text"]
        # Verify the DB row is also clean
        comment = Comment.objects.get(report=own_report)
        assert "<script>" not in comment.text

    def test_comment_strips_event_handler_attributes(self, api_client, verified_user, own_report):
        """Inline event handlers (onerror=, onload=) must not survive sanitization."""
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"/api/reports/{own_report.id}/comment/",
            {"text": '<img src=x onerror="alert(1)"> check this'},
            format="json",
        )
        assert resp.status_code == 201
        assert "onerror" not in resp.data["text"]
        assert "<img" not in resp.data["text"]

    def test_comment_preserves_plain_text(self, api_client, verified_user, own_report):
        """Sanitization must not alter plain text that contains no HTML."""
        plain = "Steps: 1) open the page 2) click submit — it breaks."
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"/api/reports/{own_report.id}/comment/",
            {"text": plain},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["text"] == plain


# ---------------------------------------------------------------------------
# Submit for review
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSubmitForReview:
    def test_owner_can_submit_open_report_for_review(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(f"/api/reports/{own_report.id}/submit_for_review/")
        assert resp.status_code == 200
        own_report.refresh_from_db()
        assert own_report.status == "triaged"

    def test_cannot_submit_already_triaged_report(self, api_client, verified_user, triaged_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(f"/api/reports/{triaged_report.id}/submit_for_review/")
        assert resp.status_code == 400

    def test_other_user_cannot_submit_report_for_review(self, api_client, second_verified_user, own_report):
        api_client.force_authenticate(user=second_verified_user)
        resp = api_client.post(f"/api/reports/{own_report.id}/submit_for_review/")
        # Either 403 (permission denied by object permission) or 404 (scoped queryset)
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Triage actions: accept, reject, reopen
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTriageActions:
    def test_triager_can_accept_triaged_report(self, api_client, triager_user, triaged_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(
            f"/api/reports/{triaged_report.id}/accept/",
            {"verification_notes": "Confirmed — reproduced locally.", "bonus_points": 25},
            format="json",
        )
        assert resp.status_code == 200
        triaged_report.refresh_from_db()
        assert triaged_report.status == "accepted"
        assert triaged_report.bonus_points == 25

    def test_researcher_cannot_accept_report(self, api_client, verified_user, triaged_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(f"/api/reports/{triaged_report.id}/accept/")
        assert resp.status_code == 403

    def test_triager_can_reject_triaged_report(self, api_client, triager_user, triaged_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(
            f"/api/reports/{triaged_report.id}/reject/",
            {"rejection_reason": "Out of scope for this program."},
            format="json",
        )
        assert resp.status_code == 200
        triaged_report.refresh_from_db()
        assert triaged_report.status == "rejected"

    def test_researcher_cannot_reject_report(self, api_client, verified_user, triaged_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(f"/api/reports/{triaged_report.id}/reject/")
        assert resp.status_code == 403

    def test_triager_can_reopen_accepted_report(self, api_client, triager_user, triaged_report):
        # First accept it
        triaged_report.status = "accepted"
        triaged_report.save()

        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(f"/api/reports/{triaged_report.id}/reopen/")
        assert resp.status_code == 200
        triaged_report.refresh_from_db()
        assert triaged_report.status == "triaged"

    def test_cannot_reopen_open_report(self, api_client, triager_user, own_report):
        """An open report is not in a closeable state so reopen should fail."""
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(f"/api/reports/{own_report.id}/reopen/")
        assert resp.status_code == 400

    def test_researcher_cannot_reopen_report(self, api_client, verified_user, triaged_report):
        triaged_report.status = "accepted"
        triaged_report.save()
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(f"/api/reports/{triaged_report.id}/reopen/")
        assert resp.status_code == 403

    def test_accept_open_report_fails(self, api_client, triager_user, own_report):
        """Only triaged/accepted reports can be accepted — open cannot."""
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(f"/api/reports/{own_report.id}/accept/")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Assign to me
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAssignToMe:
    def test_triager_can_assign_report_to_themselves(self, api_client, triager_user, own_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(f"/api/reports/{own_report.id}/assign_to_me/")
        assert resp.status_code == 200
        own_report.refresh_from_db()
        assert own_report.assigned_to == triager_user

    def test_researcher_cannot_assign_report(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(f"/api/reports/{own_report.id}/assign_to_me/")
        assert resp.status_code == 403

    def test_assign_response_contains_assignee_username(self, api_client, triager_user, own_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(f"/api/reports/{own_report.id}/assign_to_me/")
        assert resp.status_code == 200
        assert resp.data.get("assigned_to") == triager_user.username


# ---------------------------------------------------------------------------
# Activity logs
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestActivityLogs:
    def test_owner_can_view_activity_log_of_own_report(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(f"/api/reports/{own_report.id}/activity_logs/")
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_triager_can_view_activity_log_of_any_report(self, api_client, triager_user, other_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.get(f"/api/reports/{other_report.id}/activity_logs/")
        assert resp.status_code == 200

    def test_accept_creates_activity_log_entry(self, api_client, triager_user, triaged_report):
        api_client.force_authenticate(user=triager_user)
        api_client.post(
            f"/api/reports/{triaged_report.id}/accept/",
            {"verification_notes": "Confirmed."},
            format="json",
        )
        assert ActivityLog.objects.filter(
            report=triaged_report, action="accept"
        ).exists()

    def test_assign_creates_activity_log_entry(self, api_client, triager_user, own_report):
        api_client.force_authenticate(user=triager_user)
        api_client.post(f"/api/reports/{own_report.id}/assign_to_me/")
        assert ActivityLog.objects.filter(
            report=own_report, action="assignment"
        ).exists()

    def test_researcher_cannot_view_others_activity_log(self, api_client, verified_user, other_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(f"/api/reports/{other_report.id}/activity_logs/")
        # Queryset-scoped: 404 is the expected security behavior (report not in user's queryset).
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Triage dashboard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTriageDashboard:
    URL = "/api/reports/triage_dashboard/"

    def test_triager_can_access_triage_dashboard(self, api_client, triager_user):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert "counts" in resp.data
        assert "recent_reports" in resp.data

    def test_dashboard_counts_include_expected_keys(self, api_client, triager_user, own_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.get(self.URL)
        counts = resp.data["counts"]
        for key in ("total", "open", "triaged", "accepted", "rejected", "unassigned"):
            assert key in counts, f"Expected key '{key}' in dashboard counts"

    def test_dashboard_counts_reflect_existing_reports(self, api_client, triager_user, own_report, other_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.get(self.URL)
        assert resp.data["counts"]["total"] >= 2

    def test_researcher_cannot_access_triage_dashboard(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 403

    def test_admin_can_access_triage_dashboard(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# My submissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMySubmissions:
    URL = "/api/reports/my_submissions/"

    def test_returns_only_current_users_reports(self, api_client, verified_user, own_report, other_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.data.get("results", resp.data)]
        assert own_report.id in ids
        assert other_report.id not in ids

    def test_filter_by_status(self, api_client, verified_user, own_report, triaged_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL, {"status": "open"})
        assert resp.status_code == 200
        statuses = [r["status"] for r in resp.data.get("results", resp.data)]
        assert all(s == "open" for s in statuses)

    def test_filter_by_severity(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL, {"severity": "low"})
        assert resp.status_code == 200
        severities = [r["severity"] for r in resp.data.get("results", resp.data)]
        assert all(s == "low" for s in severities)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStats:
    URL = "/api/reports/stats/"

    def test_returns_stats_for_current_user(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        data = resp.data
        assert "total_submissions" in data
        assert "by_status" in data
        assert "by_severity" in data

    def test_total_submissions_count_is_accurate(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.data["total_submissions"] == 1

    def test_stats_do_not_include_other_users_reports(
        self, api_client, verified_user, own_report, other_report
    ):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        # verified_user has 1 report, not 2
        assert resp.data["total_submissions"] == 1

    def test_empty_stats_for_new_user(self, api_client, second_verified_user):
        api_client.force_authenticate(user=second_verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["total_submissions"] == 0


# ---------------------------------------------------------------------------
# Change status (via dedicated endpoint)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChangeStatus:
    def test_triager_can_change_status_to_any_valid_value(self, api_client, triager_user, own_report):
        api_client.force_authenticate(user=triager_user)
        for new_status in ("triaged", "open"):
            resp = api_client.patch(
                f"/api/reports/{own_report.id}/change_status/",
                {"status": new_status},
                format="json",
            )
            assert resp.status_code == 200
            assert resp.data["status"] == new_status

    def test_invalid_status_returns_400(self, api_client, triager_user, own_report):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.patch(
            f"/api/reports/{own_report.id}/change_status/",
            {"status": "nonexistent_status"},
            format="json",
        )
        assert resp.status_code == 400

    def test_researcher_cannot_change_status(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(
            f"/api/reports/{own_report.id}/change_status/",
            {"status": "triaged"},
            format="json",
        )
        assert resp.status_code == 403
