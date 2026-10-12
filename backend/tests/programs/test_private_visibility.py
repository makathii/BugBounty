"""
Private programs: who can find them, who can read their targets, and the apply -> approve -> report path.

Found by the full-program browser test: researchers could not even open a private program that takes
applications (so nobody could ever apply), nor one they were invited to (so nobody could accept).
"""
import pytest
from django.contrib.auth.models import User

from programs.models import Program, ProgramApplication, ProgramInvitation, Scope


@pytest.fixture
def owner(company_user_with_profile):
    return company_user_with_profile


@pytest.fixture
def make_private(owner):
    def make(**fields):
        defaults = dict(company=owner, name=f"Vault {Program.objects.count()}", description="Secret work.",
                        scope_type="private", status="active")
        program = Program.objects.create(**{**defaults, **fields})
        Scope.objects.create(program=program, target="*.vault.example", target_type="web_application", is_in_scope=True)
        program.testing_guidelines = "Only touch the staging cluster."
        program.report_guidelines = "Include a HAR file."
        program.save()
        return program
    return make


def names(client, url="/api/programs/researcher/"):
    data = client.get(url).data
    return [p["name"] for p in (data["results"] if isinstance(data, dict) else data)]


def detail(client, program):
    return client.get(f"/api/programs/programs/{program.id}/")


@pytest.mark.django_db
class TestDiscovery:
    def test_a_private_program_that_takes_applications_can_be_found_and_opened(self, api_client, verified_user, make_private):
        program = make_private(requires_application=True)
        api_client.force_authenticate(user=verified_user)
        assert program.name in names(api_client)
        assert detail(api_client, program).status_code == 200

    def test_an_invitation_only_program_is_invisible_without_an_invitation(self, api_client, verified_user, make_private):
        program = make_private(invitation_only=True)
        api_client.force_authenticate(user=verified_user)
        assert program.name not in names(api_client)
        assert detail(api_client, program).status_code == 404

    def test_a_pending_invitation_makes_it_visible(self, api_client, verified_user, owner, make_private):
        program = make_private(invitation_only=True)
        ProgramInvitation.objects.create(program=program, researcher=verified_user, invited_by=owner)
        api_client.force_authenticate(user=verified_user)
        assert program.name in names(api_client)
        assert detail(api_client, program).data["my_invitation"]["status"] == "pending"

    def test_someone_elses_invitation_does_not_help(self, api_client, verified_user, second_verified_user, owner, make_private):
        program = make_private(invitation_only=True)
        ProgramInvitation.objects.create(program=program, researcher=second_verified_user, invited_by=owner)
        api_client.force_authenticate(user=verified_user)
        assert program.name not in names(api_client)

    def test_a_private_program_with_neither_is_not_listed(self, api_client, verified_user, make_private):
        program = make_private()
        api_client.force_authenticate(user=verified_user)
        assert program.name not in names(api_client)

    @pytest.mark.parametrize("status", ["draft", "paused", "closed"])
    def test_inactive_programs_stay_hidden(self, api_client, verified_user, make_private, status):
        program = make_private(requires_application=True, status=status)
        api_client.force_authenticate(user=verified_user)
        assert program.name not in names(api_client)
        assert detail(api_client, program).status_code == 404


@pytest.mark.django_db
class TestWhatIsHiddenUntilAccess:
    def test_targets_and_guidelines_are_hidden_from_applicants(self, api_client, verified_user, make_private):
        program = make_private(requires_application=True)
        api_client.force_authenticate(user=verified_user)
        data = detail(api_client, program).data
        assert data["user_has_access"] is False
        assert data["scopes"] == [] and data["in_scope_count"] == 0
        assert data["testing_guidelines"] == "" and data["report_guidelines"] == ""
        assert "vault.example" not in str(data)
        assert data["description"] == "Secret work."  # enough to decide whether to apply

    def test_they_appear_once_the_application_is_approved(self, api_client, verified_user, owner, make_private):
        program = make_private(requires_application=True)
        application = ProgramApplication.objects.create(program=program, researcher=verified_user, message="Hi")
        application.approve(reviewed_by=owner, notes="ok")
        api_client.force_authenticate(user=verified_user)
        data = detail(api_client, program).data
        assert data["user_has_access"] is True
        assert [s["target"] for s in data["scopes"]] == ["*.vault.example"]
        assert data["testing_guidelines"] == "Only touch the staging cluster."

    def test_the_company_and_admins_always_see_everything(self, api_client, owner, admin_user, make_private):
        program = make_private(requires_application=True)
        for user in (owner, admin_user):
            api_client.force_authenticate(user=user)
            assert len(detail(api_client, program).data["scopes"]) == 1

    def test_public_programs_are_unaffected(self, api_client, verified_user, program):
        Scope.objects.create(program=program, target="*.public.example", target_type="web_application", is_in_scope=True)
        api_client.force_authenticate(user=verified_user)
        assert len(detail(api_client, program).data["scopes"]) == 1


@pytest.mark.django_db
class TestApplyingEndToEnd:
    def apply(self, client, program):
        return client.post(f"/api/programs/programs/{program.id}/join/", {"message": "I would love to help"}, format="json")

    def report(self, client, program):
        return client.post("/api/reports/", {
            "title": "Broken access control in the vault", "program": program.id,
            "description": "Any logged in user can read any other user's documents by changing the id. " * 2,
        }, format="json")

    def test_apply_then_wait_then_approved_then_report(self, api_client, verified_user, owner, make_private):
        program = make_private(requires_application=True)
        api_client.force_authenticate(user=verified_user)

        assert self.apply(api_client, program).status_code == 201
        assert detail(api_client, program).data["my_application"]["status"] == "pending"
        assert self.report(api_client, program).status_code == 400          # not in yet

        application = ProgramApplication.objects.get(program=program, researcher=verified_user)
        api_client.force_authenticate(user=owner)
        assert api_client.post(
            f"/api/programs/{program.id}/applications/{application.id}/approve/", {"review_notes": "Welcome"}, format="json"
        ).status_code == 200

        api_client.force_authenticate(user=verified_user)
        assert detail(api_client, program).data["my_application"]["status"] == "approved"
        assert self.report(api_client, program).status_code == 201          # now allowed

    def test_a_rejected_application_stays_out(self, api_client, verified_user, owner, make_private):
        program = make_private(requires_application=True)
        api_client.force_authenticate(user=verified_user)
        self.apply(api_client, program)
        application = ProgramApplication.objects.get(program=program, researcher=verified_user)
        api_client.force_authenticate(user=owner)
        api_client.post(f"/api/programs/{program.id}/applications/{application.id}/reject/", {}, format="json")
        api_client.force_authenticate(user=verified_user)
        assert detail(api_client, program).data["my_application"]["status"] == "rejected"
        assert detail(api_client, program).data["scopes"] == []
        assert self.report(api_client, program).status_code == 400

    def test_applications_are_private_to_their_author(self, api_client, verified_user, second_verified_user, make_private):
        program = make_private(requires_application=True)
        api_client.force_authenticate(user=second_verified_user)
        self.apply(api_client, program)
        api_client.force_authenticate(user=verified_user)
        assert detail(api_client, program).data["my_application"] is None

    def test_accepting_an_invitation_grants_access(self, api_client, verified_user, owner, make_private):
        program = make_private(invitation_only=True)
        ProgramInvitation.objects.create(program=program, researcher=verified_user, invited_by=owner)
        api_client.force_authenticate(user=verified_user)
        assert api_client.post(f"/api/programs/programs/{program.id}/join/").status_code == 200
        assert detail(api_client, program).data["user_has_access"] is True
        assert self.report(api_client, program).status_code == 201


@pytest.mark.django_db
class TestListSaysWhereYouCanReport:
    def flags(self, client):
        data = client.get("/api/programs/researcher/").data
        rows = data["results"] if isinstance(data, dict) else data
        return {p["name"]: p["user_has_access"] for p in rows}

    def test_public_open_private_closed_until_approved(self, api_client, verified_user, owner, program, make_private):
        discoverable = make_private(requires_application=True)
        api_client.force_authenticate(user=verified_user)
        flags = self.flags(api_client)
        assert flags[program.name] is True and flags[discoverable.name] is False

        ProgramApplication.objects.create(program=discoverable, researcher=verified_user).approve(reviewed_by=owner)
        assert self.flags(api_client)[discoverable.name] is True

    def test_the_company_has_access_to_its_own_programs(self, api_client, owner, make_private):
        program = make_private(requires_application=True)
        api_client.force_authenticate(user=owner)
        data = api_client.get("/api/programs/company/").data
        rows = data["results"] if isinstance(data, dict) else data
        assert {p["name"]: p["user_has_access"] for p in rows}[program.name] is True

    def test_listing_costs_a_constant_number_of_queries(
        self, api_client, verified_user, make_private, django_assert_max_num_queries
    ):
        for _ in range(12):
            make_private(requires_application=True)
        api_client.force_authenticate(user=verified_user)
        with django_assert_max_num_queries(20):
            assert api_client.get("/api/programs/researcher/").status_code == 200
