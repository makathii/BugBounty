"""Inviting researchers to a private program (the company side of private programs)."""
import pytest
from django.contrib.auth.models import Group, User
from django.core import mail

from programs.models import Program, ProgramInvitation
from reports.models import BugReport


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


def url(program, suffix=""):
    return f"/api/programs/{program.id}/invitations/{suffix}"


def invite(client, owner, program, **data):
    client.force_authenticate(user=owner)
    return client.post(url(program), data, format="json")


@pytest.mark.django_db
class TestSending:
    def test_invite_by_username(self, api_client, owner, private, ada):
        resp = invite(api_client, owner, private, username="ada", message="We liked your write-ups.")
        assert resp.status_code == 201, resp.data
        assert resp.data["status"] == "pending" and resp.data["researcher"]["username"] == "ada"
        row = ProgramInvitation.objects.get(program=private, researcher=ada)
        assert row.invited_by == owner and row.message == "We liked your write-ups."

    def test_username_is_case_insensitive_and_trimmed(self, api_client, owner, private, ada):
        assert invite(api_client, owner, private, username="  ADA ").status_code == 201

    def test_the_old_researcher_id_form_still_works(self, api_client, owner, private, ada):
        assert invite(api_client, owner, private, researcher_id=ada.id).status_code == 201

    def test_an_unknown_username_is_a_clear_error(self, api_client, owner, private):
        resp = invite(api_client, owner, private, username="nobody-here")
        assert resp.status_code == 400 and "username" in resp.data
        assert not ProgramInvitation.objects.exists()

    def test_a_username_or_id_is_required(self, api_client, owner, private):
        assert invite(api_client, owner, private).status_code == 400

    @pytest.mark.parametrize("group", ["Triager", "Admin", "ProgramOwner"])
    def test_only_researchers_can_be_invited(self, api_client, owner, private, group):
        other = User.objects.create_user(f"{group.lower()}1", f"{group}@example.com", "x" * 12, is_active=True)
        other.groups.add(Group.objects.get_or_create(name=group)[0])
        resp = invite(api_client, owner, private, username=other.username)
        assert resp.status_code == 400 and not ProgramInvitation.objects.exists()

    def test_inactive_accounts_cannot_be_invited(self, api_client, owner, private, ada):
        ada.is_active = False
        ada.save()
        assert invite(api_client, owner, private, username="ada").status_code == 400

    def test_only_private_programs_take_invitations(self, api_client, owner, ada):
        public = Program.objects.create(company=owner, name="Open", description="d", scope_type="public", status="active")
        assert invite(api_client, owner, public, username="ada").status_code == 400

    def test_only_the_owner_can_invite(self, api_client, private, ada, verified_user):
        other = User.objects.create_user("rival", "rival@example.com", "x" * 12, is_active=True)
        other.groups.add(Group.objects.get_or_create(name="ProgramOwner")[0])
        for user in (other, verified_user):
            api_client.force_authenticate(user=user)
            resp = api_client.post(url(private), {"username": "ada"}, format="json")
            assert resp.status_code in (400, 403, 404)
        assert not ProgramInvitation.objects.exists()

    def test_an_admin_can_invite(self, api_client, admin_user, private, ada):
        assert invite(api_client, admin_user, private, username="ada").status_code == 201


@pytest.mark.django_db
class TestInvitingAgain:
    def test_inviting_someone_who_is_already_pending_is_a_clear_error_not_a_crash(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="ada")
        resp = invite(api_client, owner, private, username="ada")
        assert resp.status_code == 400 and "already" in str(resp.data).lower()
        assert ProgramInvitation.objects.count() == 1

    def test_someone_who_already_has_access_cannot_be_invited_again(self, api_client, owner, private, ada):
        ProgramInvitation.objects.create(program=private, researcher=ada, invited_by=owner, status="accepted")
        resp = invite(api_client, owner, private, username="ada")
        assert resp.status_code == 400 and "access" in str(resp.data).lower()

    @pytest.mark.parametrize("old", ["rejected", "revoked"])
    def test_a_declined_or_withdrawn_invitation_can_be_sent_again(self, api_client, owner, private, ada, old):
        ProgramInvitation.objects.create(program=private, researcher=ada, invited_by=owner, status=old)
        resp = invite(api_client, owner, private, username="ada", message="Second try")
        assert resp.status_code == 201
        assert ProgramInvitation.objects.count() == 1
        row = ProgramInvitation.objects.get()
        assert row.status == "pending" and row.message == "Second try"

    def test_someone_with_an_approved_application_already_has_access(self, api_client, owner, private, ada):
        from programs.models import ProgramApplication
        ProgramApplication.objects.create(program=private, researcher=ada, status="approved")
        assert invite(api_client, owner, private, username="ada").status_code == 400


@pytest.mark.django_db
class TestEmail:
    def test_the_researcher_is_emailed(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="ada", message="Join us!")
        assert [m.to for m in mail.outbox] == [["ada@example.com"]]
        body = mail.outbox[0].body
        assert "Vault" in body and "Join us!" in body and f"/programs/{private.id}" in body

    def test_a_mail_failure_does_not_stop_the_invitation(self, api_client, owner, private, ada, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("smtp down")
        monkeypatch.setattr("programs.tasks.send_mail", boom)
        assert invite(api_client, owner, private, username="ada").status_code == 201

    def test_no_email_address_is_fine(self, api_client, owner, private, ada):
        ada.email = ""
        ada.save()
        assert invite(api_client, owner, private, username="ada").status_code == 201
        assert mail.outbox == []


@pytest.mark.django_db
class TestListingAndAnswering:
    def test_the_owner_sees_all_invitations_of_the_program(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="ada")
        data = api_client.get(url(private)).data
        rows = data["results"] if isinstance(data, dict) else data
        assert [r["researcher"]["username"] for r in rows] == ["ada"]

    def test_a_researcher_only_sees_their_own(self, api_client, owner, private, ada, verified_user):
        invite(api_client, owner, private, username="ada")
        api_client.force_authenticate(user=verified_user)
        data = api_client.get(url(private)).data
        assert (data["results"] if isinstance(data, dict) else data) == []

    def test_my_invitations_across_programs(self, api_client, owner, private, ada):
        other = Program.objects.create(company=owner, name="Other", description="d", scope_type="private", status="active")
        invite(api_client, owner, private, username="ada")
        invite(api_client, owner, other, username="ada")
        api_client.force_authenticate(user=ada)
        data = api_client.get("/api/programs/my-invitations/").data
        rows = data["results"] if isinstance(data, dict) else data
        assert {r["program_name"] for r in rows} == {"Vault", "Other"}
        assert all(r["status"] == "pending" for r in rows)

    def test_my_invitations_are_private_to_their_owner(self, api_client, owner, private, ada, verified_user):
        invite(api_client, owner, private, username="ada")
        api_client.force_authenticate(user=verified_user)
        data = api_client.get("/api/programs/my-invitations/").data
        assert (data["results"] if isinstance(data, dict) else data) == []
        api_client.force_authenticate(user=None)
        assert api_client.get("/api/programs/my-invitations/").status_code == 401

    def test_accepting_grants_access_to_report(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="ada")
        row = ProgramInvitation.objects.get()
        api_client.force_authenticate(user=ada)
        assert api_client.post(url(private, f"{row.id}/accept/")).status_code == 200
        ada.profile.email_verified = True
        ada.profile.save()
        resp = api_client.post("/api/reports/", {
            "title": "Broken access control", "program": private.id,
            "description": "Any user can read any other user's documents by changing the id. " * 2,
        }, format="json")
        assert resp.status_code == 201, resp.data

    def test_declining_leaves_them_out(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="ada")
        row = ProgramInvitation.objects.get()
        api_client.force_authenticate(user=ada)
        assert api_client.post(url(private, f"{row.id}/reject/")).status_code == 200
        row.refresh_from_db()
        assert row.status == "rejected"

    def test_only_the_invitee_can_answer(self, api_client, owner, private, ada, verified_user):
        invite(api_client, owner, private, username="ada")
        row = ProgramInvitation.objects.get()
        api_client.force_authenticate(user=verified_user)
        assert api_client.post(url(private, f"{row.id}/accept/")).status_code in (403, 404)
        row.refresh_from_db()
        assert row.status == "pending"

    def test_the_owner_can_withdraw_a_pending_invitation(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="ada")
        row = ProgramInvitation.objects.get()
        api_client.force_authenticate(user=owner)
        assert api_client.post(url(private, f"{row.id}/revoke/")).status_code == 200
        api_client.force_authenticate(user=ada)
        assert api_client.post(url(private, f"{row.id}/accept/")).status_code == 400  # too late

    def test_researchers_cannot_revoke(self, api_client, owner, private, ada):
        invite(api_client, owner, private, username="ada")
        row = ProgramInvitation.objects.get()
        api_client.force_authenticate(user=ada)
        assert api_client.post(url(private, f"{row.id}/revoke/")).status_code in (403, 404)
