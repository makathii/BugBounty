"""The in-app notification bell: who is told what, and the API behind it."""
import pytest
from django.contrib.auth.models import Group, User

from programs.models import Program, ProgramApplication, ProgramInvitation, ProgramNotification


@pytest.fixture
def owner(company_user_with_profile):
    return company_user_with_profile


@pytest.fixture
def private(owner):
    return Program.objects.create(
        company=owner, name="Vault", description="Secret.", scope_type="private",
        invitation_only=True, status="active",
    )


@pytest.fixture
def ada(db):
    user = User.objects.create_user("ada", "ada@example.com", "x" * 12, is_active=True)
    user.groups.add(Group.objects.get_or_create(name="Researcher")[0])
    return user


def inbox(user, kind=None):
    rows = ProgramNotification.objects.filter(user=user)
    return rows.filter(notification_type=kind) if kind else rows


def invite(client, owner, program, username="ada"):
    client.force_authenticate(user=owner)
    return client.post(f"/api/programs/{program.id}/invitations/", {"username": username}, format="json")


@pytest.mark.django_db
class TestInvitations:
    def test_invite_notifies_researcher_with_a_link(self, api_client, owner, private, ada):
        assert invite(api_client, owner, private).status_code == 201
        n = inbox(ada, "invitation").get()
        assert n.data["link"] == f"/programs/{private.id}" and not n.read

    def test_reinvite_after_revoke_notifies_again(self, api_client, owner, private, ada):
        invite(api_client, owner, private)
        row = ProgramInvitation.objects.get(program=private, researcher=ada)
        api_client.post(f"/api/programs/{private.id}/invitations/{row.id}/revoke/")
        assert inbox(ada, "invitation_revoked").count() == 1
        invite(api_client, owner, private)
        assert inbox(ada, "invitation").count() == 2

    @pytest.mark.parametrize("action,word", [("accept", "accepted"), ("reject", "declined")])
    def test_answer_notifies_the_company(self, api_client, owner, private, ada, action, word):
        invite(api_client, owner, private)
        row = ProgramInvitation.objects.get(program=private, researcher=ada)
        api_client.force_authenticate(user=ada)
        assert api_client.post(f"/api/programs/{private.id}/invitations/{row.id}/{action}/").status_code == 200
        n = inbox(owner, "invitation_answer").get()
        assert word in n.title and n.data["link"] == f"/company/programs/{private.id}/invitations"

    def test_a_failed_action_creates_nothing(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="nobody")
        assert ProgramNotification.objects.count() == 0


@pytest.mark.django_db
class TestApplications:
    def test_company_hears_about_a_new_application_and_researcher_about_the_outcome(
        self, api_client, owner, ada
    ):
        program = Program.objects.create(
            company=owner, name="Gate", description="x", scope_type="private",
            requires_application=True, status="active",
        )
        application = ProgramApplication.objects.create(program=program, researcher=ada, message="hi")
        assert inbox(owner, "application_submitted").get().data["link"].endswith("/applications")
        api_client.force_authenticate(user=owner)
        api_client.post(f"/api/programs/{program.id}/applications/{application.id}/approve/")
        assert "approved" in inbox(ada, "application_update").get().title.lower()


@pytest.mark.django_db
class TestReports:
    def test_decisions_notify_the_reporter(self, api_client, triager_user, verified_user, own_report):
        api_client.force_authenticate(user=triager_user)
        assert api_client.post(f"/api/reports/{own_report.id}/triage/", {"severity": "high"}).status_code == 200
        assert api_client.post(
            f"/api/reports/{own_report.id}/accept/", {"verification_notes": "ok", "bonus_points": 5}
        ).status_code == 200
        titles = list(inbox(verified_user, "report_decision").values_list("title", flat=True))
        assert any("triaged" in t for t in titles) and any("accepted" in t for t in titles)
        accepted = inbox(verified_user, "report_decision").filter(title__contains="accepted").get()
        assert "points" in accepted.message and accepted.data["link"] == f"/reports/{own_report.id}"

    def test_comments_notify_others_never_the_author(
        self, api_client, triager_user, verified_user, own_report
    ):
        own_report.assigned_to = triager_user
        own_report.save()
        api_client.force_authenticate(user=verified_user)
        assert api_client.post(f"/api/reports/{own_report.id}/comments/", {"text": "please look"}).status_code == 201
        assert inbox(triager_user, "report_comment").count() == 1
        assert inbox(verified_user, "report_comment").count() == 0

    def test_internal_notes_stay_away_from_the_researcher_and_company(
        self, api_client, triager_user, verified_user, own_report
    ):
        own_report.assigned_to = triager_user
        own_report.save()
        api_client.force_authenticate(user=triager_user)
        resp = api_client.post(
            f"/api/reports/{own_report.id}/comments/", {"text": "secret", "is_internal": True}, format="json"
        )
        assert resp.status_code == 201
        assert inbox(verified_user).count() == 0
        assert inbox(own_report.program.company, "report_comment").count() == 0


@pytest.mark.django_db
class TestApi:
    def test_list_count_and_marking_read(self, api_client, ada):
        for i in range(3):
            ProgramNotification.notify(ada, "invitation", f"T{i}", "m", data={"link": f"/programs/{i}"})
        api_client.force_authenticate(user=ada)
        listing = api_client.get("/api/programs/notifications/").data
        rows = listing["results"] if isinstance(listing, dict) else listing
        assert len(rows) == 3 and rows[0]["link"].startswith("/programs/")
        assert api_client.get("/api/programs/notifications/unread_count/").data["unread_count"] == 3
        assert api_client.post(f"/api/programs/notifications/{rows[0]['id']}/mark_read/").status_code == 200
        assert api_client.get("/api/programs/notifications/unread_count/").data["unread_count"] == 2
        api_client.post("/api/programs/notifications/mark_all_read/")
        assert api_client.get("/api/programs/notifications/unread_count/").data["unread_count"] == 0

    def test_people_only_see_their_own(self, api_client, ada, owner):
        n = ProgramNotification.notify(ada, "invitation", "Mine", "m")
        api_client.force_authenticate(user=owner)
        listing = api_client.get("/api/programs/notifications/").data
        assert (listing["results"] if isinstance(listing, dict) else listing) == []
        assert api_client.post(f"/api/programs/notifications/{n.id}/mark_read/").status_code == 404

    def test_a_javascript_link_is_not_exposed(self, api_client, ada):
        ProgramNotification.notify(ada, "invitation", "x", "m", data={"link": "javascript:alert(1)"})
        api_client.force_authenticate(user=ada)
        listing = api_client.get("/api/programs/notifications/").data
        rows = listing["results"] if isinstance(listing, dict) else listing
        assert rows[0]["link"] == ""
