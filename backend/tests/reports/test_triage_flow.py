"""
The full report lifecycle: submitted (open) -> triage -> accepted/rejected -> points and emails.

Found by the full-program browser test: nothing in the product could move an open report to
'triaged', and only triaged reports can be accepted, so no report could ever earn points. Also the
researcher was never told about decisions.
"""
import pytest
from django.core import mail

from leaderboard.models import ScoreEvent
from reports.models import ActivityLog, BugReport
from wallet import services as wallet


@pytest.fixture(autouse=True)
def economy(settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 70, "critical": 150}


@pytest.fixture
def reporter(own_report, verified_user):
    verified_user.email = "researcher@example.com"
    verified_user.save()
    return verified_user


def post(client, user, report, action, **data):
    client.force_authenticate(user=user)
    return client.post(f"/api/reports/{report.id}/{action}/", data, format="json")


@pytest.mark.django_db
class TestTriage:
    def test_an_open_report_moves_to_triaged_and_is_assigned(self, api_client, triager_user, own_report):
        resp = post(api_client, triager_user, own_report, "triage")
        assert resp.status_code == 200, resp.data
        own_report.refresh_from_db()
        assert own_report.status == "triaged"
        assert own_report.assigned_to == triager_user
        assert own_report.time_to_triage is not None

    def test_severity_can_be_set_while_triaging(self, api_client, triager_user, own_report):
        assert post(api_client, triager_user, own_report, "triage", severity="critical").status_code == 200
        own_report.refresh_from_db()
        assert own_report.severity == "critical"

    def test_a_bad_severity_changes_nothing(self, api_client, triager_user, own_report):
        resp = post(api_client, triager_user, own_report, "triage", severity="catastrophic")
        assert resp.status_code == 400
        own_report.refresh_from_db()
        assert own_report.status == "open" and own_report.assigned_to is None

    def test_it_does_not_steal_an_existing_assignment(self, api_client, triager_user, admin_user, own_report):
        own_report.assigned_to = admin_user
        own_report.save()
        post(api_client, triager_user, own_report, "triage")
        own_report.refresh_from_db()
        assert own_report.assigned_to == admin_user

    @pytest.mark.parametrize("status", ["triaged", "accepted", "rejected", "resolved", "closed"])
    def test_only_open_reports_can_be_triaged(self, api_client, triager_user, own_report, status):
        BugReport.objects.filter(pk=own_report.pk).update(status=status)
        assert post(api_client, triager_user, own_report, "triage").status_code == 400

    def test_researchers_cannot_triage_even_their_own(self, api_client, verified_user, own_report):
        assert post(api_client, verified_user, own_report, "triage").status_code == 403
        own_report.refresh_from_db()
        assert own_report.status == "open"

    def test_requires_login(self, api_client, own_report):
        assert api_client.post(f"/api/reports/{own_report.id}/triage/").status_code == 401

    def test_it_is_recorded_in_the_activity_log(self, api_client, triager_user, own_report):
        post(api_client, triager_user, own_report, "triage")
        log = ActivityLog.objects.get(report=own_report, action="status_change")
        assert log.details["old_status"] == "open" and log.details["new_status"] == "triaged"

    def test_the_researcher_is_told(self, api_client, triager_user, own_report, reporter):
        post(api_client, triager_user, own_report, "triage")
        assert [m.to for m in mail.outbox] == [["researcher@example.com"]]
        assert "reviewing" in mail.outbox[0].body and f"/reports/{own_report.id}" in mail.outbox[0].body


@pytest.mark.django_db
class TestAcceptAndReject:
    def triaged(self, api_client, triager_user, report, **data):
        post(api_client, triager_user, report, "triage", **data)
        mail.outbox.clear()

    def test_accepting_pays_severity_points_plus_bonus(self, api_client, triager_user, own_report, reporter):
        self.triaged(api_client, triager_user, own_report)
        resp = post(api_client, triager_user, own_report, "accept", severity="high", bonus_points=15,
                    verification_notes="Well written.")
        assert resp.status_code == 200, resp.data
        assert resp.data["severity"] == "high" and resp.data["points_awarded"] == 85
        assert ScoreEvent.objects.get(report=own_report).points == 85
        assert wallet.balance(reporter) == 85

    def test_the_severity_chosen_at_acceptance_sets_the_points(self, api_client, triager_user, own_report, reporter):
        self.triaged(api_client, triager_user, own_report, severity="low")
        post(api_client, triager_user, own_report, "accept", severity="critical")
        assert wallet.balance(reporter) == 150

    def test_without_a_severity_the_current_one_is_kept(self, api_client, triager_user, own_report, reporter):
        self.triaged(api_client, triager_user, own_report, severity="medium")
        post(api_client, triager_user, own_report, "accept")
        assert wallet.balance(reporter) == 30

    def test_a_bad_severity_at_acceptance_accepts_nothing(self, api_client, triager_user, own_report):
        self.triaged(api_client, triager_user, own_report)
        assert post(api_client, triager_user, own_report, "accept", severity="nope").status_code == 400
        own_report.refresh_from_db()
        assert own_report.status == "triaged"

    def test_an_open_report_cannot_be_accepted_without_triage(self, api_client, triager_user, own_report):
        assert post(api_client, triager_user, own_report, "accept").status_code == 400
        assert not ScoreEvent.objects.exists()

    def test_the_researcher_is_told_what_they_earned(self, api_client, triager_user, own_report, reporter):
        self.triaged(api_client, triager_user, own_report)
        post(api_client, triager_user, own_report, "accept", severity="high", bonus_points=15,
             verification_notes="Well written.")
        assert [m.to for m in mail.outbox] == [["researcher@example.com"]]
        body = mail.outbox[0].body
        assert "accepted" in mail.outbox[0].subject.lower()
        assert "85 points" in body and "15 bonus" in body and "Well written." in body

    def test_a_rejection_carries_the_reason_and_pays_nothing(self, api_client, triager_user, own_report, reporter):
        self.triaged(api_client, triager_user, own_report)
        resp = post(api_client, triager_user, own_report, "reject", rejection_reason="Cannot reproduce.")
        assert resp.status_code == 200
        assert wallet.balance(reporter) == 0
        assert "Cannot reproduce." in mail.outbox[0].body and "rejected" in mail.outbox[0].body.lower()

    def test_a_mail_failure_does_not_undo_the_decision(
        self, api_client, triager_user, own_report, reporter, monkeypatch
    ):
        self.triaged(api_client, triager_user, own_report)

        def boom(*a, **k):
            raise RuntimeError("smtp down")

        monkeypatch.setattr("reports.tasks.send_mail", boom)
        resp = post(api_client, triager_user, own_report, "accept", severity="low")
        assert resp.status_code == 200
        own_report.refresh_from_db()
        assert own_report.status == "accepted" and wallet.balance(reporter) == 10

    def test_a_researcher_without_an_email_is_simply_not_emailed(self, api_client, triager_user, own_report, verified_user):
        verified_user.email = ""
        verified_user.save()
        self.triaged(api_client, triager_user, own_report)
        assert post(api_client, triager_user, own_report, "accept").status_code == 200
        assert mail.outbox == []


@pytest.mark.django_db
def test_the_whole_journey_over_the_api(api_client, triager_user, verified_user, program):
    """Submit -> triage -> accept: the researcher ends up with points, a level and a badge."""
    from badges.models import UserBadge

    verified_user.email = "ada@example.com"
    verified_user.save()
    api_client.force_authenticate(user=verified_user)
    created = api_client.post("/api/reports/", {
        "title": "Open redirect on the login page", "program": program.id,
        "description": "The return_url parameter is not validated, so any site can be the redirect target. " * 2,
    }, format="json")
    assert created.status_code == 201, created.data
    report = BugReport.objects.get(pk=created.data["id"])
    assert report.status == "open" and wallet.balance(verified_user) == 0

    assert post(api_client, triager_user, report, "triage", severity="medium").status_code == 200
    assert post(api_client, triager_user, report, "accept", bonus_points=5).status_code == 200

    summary = wallet.summary(verified_user)
    assert summary["balance"] == 35 and summary["lifetime_earned"] == 35
    assert UserBadge.objects.filter(user=verified_user, key="first_blood").exists()
