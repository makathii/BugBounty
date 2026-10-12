"""
What a program owner (company) may do with reports filed against its programs.

Found by the full-program browser test: the report list included the company's reports, but opening
one was refused (403), so companies could not read, or discuss, the reports they were sent.
Companies read and talk; they do not edit, delete, triage or pay out.
"""
import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from programs.models import Company, Program
from reports.models import BugReport, Comment


@pytest.fixture
def owner(company_user_with_profile):
    return company_user_with_profile


@pytest.fixture
def owner_report(db, verified_user, active_program):
    return BugReport.objects.create(
        title="Auth bypass on the Acme API", description="A long enough description of the bypass " * 3,
        reporter=verified_user, program=active_program, severity="high",
    )


@pytest.fixture
def other_owner(db, program_owner_group):
    user = User.objects.create_user("other_owner", "other@example.com", "SafePass123!", is_active=True)
    user.groups.add(program_owner_group)
    return user


def as_user(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestReading:
    def test_the_owner_can_open_a_report_filed_against_their_program(self, owner, owner_report):
        resp = as_user(owner).get(f"/api/reports/{owner_report.id}/")
        assert resp.status_code == 200 and resp.data["title"] == owner_report.title

    def test_the_owner_sees_it_in_their_list(self, owner, owner_report):
        data = as_user(owner).get("/api/reports/").data
        rows = data["results"] if isinstance(data, dict) else data
        assert owner_report.id in [r["id"] for r in rows]

    def test_another_company_cannot_open_it(self, other_owner, owner_report):
        assert as_user(other_owner).get(f"/api/reports/{owner_report.id}/").status_code in (403, 404)

    def test_a_company_cannot_open_reports_on_other_companies_programs(self, other_owner, owner_report, verified_user):
        rival_program = Program.objects.create(
            company=other_owner, name="Rival", description="d", scope_type="public", status="active",
        )
        rival_report = BugReport.objects.create(
            title="A report for the rival", description="x" * 60, reporter=verified_user, program=rival_program,
        )
        # `other_owner` may read their own program's report but not the first company's
        assert as_user(other_owner).get(f"/api/reports/{rival_report.id}/").status_code == 200
        assert as_user(other_owner).get(f"/api/reports/{owner_report.id}/").status_code in (403, 404)

    def test_activity_log_hides_internal_entries(self, owner, owner_report, triager_user):
        staff = as_user(triager_user)
        staff.post(f"/api/reports/{owner_report.id}/comments/", {"text": "staff only", "is_internal": True}, format="json")
        logs = as_user(owner).get(f"/api/reports/{owner_report.id}/activity_logs/")
        assert logs.status_code == 200
        assert not [l for l in logs.data if l["action"] == "comment"]

    def test_the_owner_can_list_attachments(self, owner, owner_report):
        assert as_user(owner).get(f"/api/reports/{owner_report.id}/attachments/").status_code == 200


@pytest.mark.django_db
class TestDiscussing:
    def test_the_owner_can_comment_and_the_researcher_sees_it(self, owner, owner_report, verified_user):
        resp = as_user(owner).post(
            f"/api/reports/{owner_report.id}/comments/", {"text": "Can you share the request?"}, format="json"
        )
        assert resp.status_code == 201
        thread = as_user(verified_user).get(f"/api/reports/{owner_report.id}/comments/").data
        assert [c["text"] for c in thread] == ["Can you share the request?"]

    def test_the_owner_cannot_post_internal_notes_or_see_them(self, owner, owner_report, triager_user):
        denied = as_user(owner).post(
            f"/api/reports/{owner_report.id}/comments/", {"text": "x", "is_internal": True}, format="json"
        )
        assert denied.status_code == 403
        Comment.objects.create(report=owner_report, author=triager_user, text="secret", is_internal=True)
        thread = as_user(owner).get(f"/api/reports/{owner_report.id}/comments/").data
        assert thread == []

    def test_another_company_cannot_comment(self, other_owner, owner_report):
        resp = as_user(other_owner).post(f"/api/reports/{owner_report.id}/comments/", {"text": "hi"}, format="json")
        assert resp.status_code in (403, 404)
        assert not Comment.objects.exists()


@pytest.mark.django_db
class TestWhatCompaniesCannotDo:
    def test_edit_or_delete_a_report(self, owner, owner_report):
        client = as_user(owner)
        assert client.patch(f"/api/reports/{owner_report.id}/", {"title": "Hijacked title here"}, format="json").status_code == 403
        assert client.delete(f"/api/reports/{owner_report.id}/").status_code == 403
        owner_report.refresh_from_db()
        assert owner_report.title == "Auth bypass on the Acme API"

    @pytest.mark.parametrize("action", ["triage", "accept", "reject", "assign_to_me", "reopen"])
    def test_triage_or_pay_out(self, owner, owner_report, action):
        BugReport.objects.filter(pk=owner_report.pk).update(status="triaged")
        assert as_user(owner).post(f"/api/reports/{owner_report.id}/{action}/", {}, format="json").status_code == 403
        owner_report.refresh_from_db()
        assert owner_report.status == "triaged" and owner_report.bonus_points == 0

    def test_change_status(self, owner, owner_report):
        resp = as_user(owner).patch(f"/api/reports/{owner_report.id}/change_status/", {"status": "accepted"}, format="json")
        assert resp.status_code == 403

    def test_upload_attachments(self, owner, owner_report):
        resp = as_user(owner).post(f"/api/reports/{owner_report.id}/upload_attachment/", {}, format="multipart")
        assert resp.status_code in (403, 400) and owner_report.attachments.count() == 0
