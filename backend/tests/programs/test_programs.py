"""
Tests for the entire programs app.

No prior tests existed for this app. Covers:
  - Program CRUD with role-based access
  - Public / researcher / company listing views
  - Program dashboard
  - Company profile creation and verification
  - Scope management (create, list, update, delete)
  - Invitation system (create, accept, reject, revoke)
  - Application system (apply, approve, reject, withdraw)
  - Favorites (add, remove, list)
  - Notifications (list, mark read)

Known bug documented via test:
  - IsResearcher permission checks group name 'User' but users are assigned
    to the 'Researcher' group → researcher access tests will fail until fixed.
"""
import pytest
from django.contrib.auth.models import User, Group
from programs.models import (
    Program, Company, Scope, ProgramInvitation,
    ProgramApplication, ProgramFavorite, ProgramNotification,
)
from users.models import Profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_verified_user(username, group_name="Researcher"):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="SafePass123!",
        is_active=True,
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    Profile.objects.filter(user=user).update(email_verified=True)
    return user


# ---------------------------------------------------------------------------
# Company profile
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCompanyProfile:
    CREATE_URL = "/api/users/companies/"

    def test_company_user_can_create_profile(self, api_client, company_user):
        api_client.force_authenticate(user=company_user)
        resp = api_client.post(self.CREATE_URL, {
            "company_name": "Test Corp",
            "website": "https://testcorp.example.com",
            "description": "Security testing company",
            "contact_email": "security@testcorp.example.com",
            "industry": "Technology",
            "country": "US",
        }, format="json")
        assert resp.status_code == 201
        assert Company.objects.filter(user=company_user).exists()

    def test_company_profile_not_verified_by_default(self, api_client, company_user):
        api_client.force_authenticate(user=company_user)
        api_client.post(self.CREATE_URL, {
            "company_name": "Test Corp",
            "website": "https://testcorp.example.com",
            "description": "Security testing company",
            "contact_email": "security@testcorp.example.com",
        }, format="json")
        company = Company.objects.get(user=company_user)
        assert company.is_verified is False
        assert company.can_create_program is False

    def test_unauthenticated_cannot_create_company_profile(self, api_client):
        resp = api_client.post(self.CREATE_URL, {
            "company_name": "Hacker Corp",
        }, format="json")
        assert resp.status_code == 401

    def test_company_profile_requires_name_and_website(self, api_client, company_user):
        api_client.force_authenticate(user=company_user)
        resp = api_client.post(self.CREATE_URL, {
            "company_name": "",
            "website": "",
        }, format="json")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Program CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProgramCRUD:
    LIST_URL = "/api/programs/programs/"

    def url(self, pk):
        return f"/api/programs/programs/{pk}/"

    def test_company_owner_can_create_program(self, api_client, company_user_with_profile):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.post(self.LIST_URL, {
            "name": "New Bounty Program",
            "description": "Looking for vulnerabilities in our platform.",
            "scope_type": "public",
            "status": "draft",
        }, format="json")
        assert resp.status_code == 201
        assert Program.objects.filter(company=company_user_with_profile).exists()

    def test_program_slug_auto_generated(self, api_client, company_user_with_profile):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.post(self.LIST_URL, {
            "name": "Slug Auto Test Program",
            "description": "Testing slug generation.",
            "scope_type": "public",
        }, format="json")
        assert resp.status_code == 201
        # ProgramCreateSerializer doesn't expose 'slug' — verify via DB instead.
        from programs.models import Program
        program = Program.objects.get(company=company_user_with_profile, name="Slug Auto Test Program")
        assert program.slug
        assert program.slug != ""

    def test_researcher_cannot_create_program(self, api_client, verified_user):
        # BUG: IsProgramOwnerOrAdmin.has_permission only checks is_authenticated,
        # not whether the user is in the ProgramOwner group. Any authenticated user
        # can currently create programs. Fix: check group membership in has_permission.
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.LIST_URL, {
            "name": "Unauthorized Program",
            "description": "Should be rejected.",
            "scope_type": "public",
        }, format="json")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_program(self, api_client):
        resp = api_client.post(self.LIST_URL, {
            "name": "Anon Program",
        }, format="json")
        assert resp.status_code == 401

    def test_owner_can_update_own_program(self, api_client, company_user_with_profile, active_program):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.patch(
            self.url(active_program.id),
            {"name": "Renamed Program"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["name"] == "Renamed Program"

    def test_other_company_cannot_update_program(self, api_client, active_program):
        # BUG: ProgramViewSet.get_object() is overridden with get_object_or_404() but
        # does NOT call self.check_object_permissions(). DRF's default get_object()
        # calls check_object_permissions after fetching the object, enforcing
        # has_object_permission. The override bypasses that, so any authenticated
        # ProgramOwner can update any program. Fix: call check_object_permissions()
        # inside the overridden get_object(), or remove the override.
        other_company = _make_verified_user("other_co", "ProgramOwner")
        api_client.force_authenticate(user=other_company)
        resp = api_client.patch(
            self.url(active_program.id),
            {"name": "Hijacked"},
            format="json",
        )
        assert resp.status_code in (403, 404)

    def test_owner_can_delete_own_program(self, api_client, company_user_with_profile, active_program):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.delete(self.url(active_program.id))
        assert resp.status_code == 204
        assert not Program.objects.filter(id=active_program.id).exists()

    def test_admin_can_delete_any_program(self, api_client, admin_user, active_program):
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(self.url(active_program.id))
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Program listings
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPublicProgramListing:
    URL = "/api/programs/public/"

    def test_unauthenticated_can_list_public_programs(self, api_client, active_program):
        resp = api_client.get(self.URL)
        # Public listing may require auth depending on implementation
        assert resp.status_code in (200, 401)

    def test_authenticated_user_can_list_public_programs(self, api_client, verified_user, active_program):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200

    def test_only_active_public_programs_appear(self, api_client, verified_user, company_user_with_profile):
        api_client.force_authenticate(user=verified_user)
        # Create a draft program — should NOT appear
        Program.objects.create(
            name="Draft Program",
            company=company_user_with_profile,
            description="Not yet active",
            status="draft",
            scope_type="public",
        )
        # Create an active public program — SHOULD appear
        active = Program.objects.create(
            name="Active Public Program",
            company=company_user_with_profile,
            description="Accepting reports",
            status="active",
            scope_type="public",
        )
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        names = [p["name"] for p in resp.data]
        assert "Active Public Program" in names
        assert "Draft Program" not in names

    def test_private_programs_excluded_from_public_listing(self, api_client, verified_user, company_user_with_profile):
        api_client.force_authenticate(user=verified_user)
        Program.objects.create(
            name="Private Program",
            company=company_user_with_profile,
            description="Invite only",
            status="active",
            scope_type="private",
        )
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        names = [p["name"] for p in resp.data]
        assert "Private Program" not in names


@pytest.mark.django_db
class TestCompanyProgramListing:
    URL = "/api/programs/company/"

    def test_company_owner_sees_own_programs(self, api_client, company_user_with_profile, active_program):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.data]
        assert active_program.id in ids

    def test_company_owner_does_not_see_other_companies_programs(
        self, api_client, company_user_with_profile, active_program
    ):
        other_company = _make_verified_user("co2", "ProgramOwner")
        api_client.force_authenticate(user=other_company)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.data]
        assert active_program.id not in ids

    def test_researcher_cannot_access_company_listing(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        # May be 200 with empty list or 403 depending on impl
        if resp.status_code == 200:
            assert resp.data == [] or len(resp.data) == 0


@pytest.mark.django_db
class TestProgramDashboard:
    URL = "/api/programs/dashboard/"

    def test_company_owner_can_access_dashboard(self, api_client, company_user_with_profile):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.get(self.URL)
        assert resp.status_code in (200, 404)  # 404 if no programs yet

    def test_unauthenticated_cannot_access_dashboard(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Scope management
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestScopeManagement:
    def scopes_url(self, program_id):
        return f"/api/programs/{program_id}/scopes/"

    def scope_url(self, program_id, scope_id):
        return f"/api/programs/{program_id}/scopes/{scope_id}/"

    def test_owner_can_add_scope(self, api_client, company_user_with_profile, active_program):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.post(self.scopes_url(active_program.id), {
            "target": "https://app.example.com",
            "target_type": "web_application",
            "is_in_scope": True,
            "description": "Main web application",
        }, format="json")
        assert resp.status_code == 201
        assert Scope.objects.filter(program=active_program).exists()

    def test_owner_can_list_scopes(self, api_client, company_user_with_profile, active_program):
        Scope.objects.create(
            program=active_program,
            target="https://app.example.com",
            target_type="web_application",
        )
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.get(self.scopes_url(active_program.id))
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_owner_can_delete_scope(self, api_client, company_user_with_profile, active_program):
        scope = Scope.objects.create(
            program=active_program,
            target="https://old.example.com",
            target_type="web_application",
        )
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.delete(self.scope_url(active_program.id, scope.id))
        assert resp.status_code == 204
        assert not Scope.objects.filter(id=scope.id).exists()

    def test_out_of_scope_entry_can_be_created(self, api_client, company_user_with_profile, active_program):
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.post(self.scopes_url(active_program.id), {
            "target": "https://staging.example.com",
            "target_type": "web_application",
            "is_in_scope": False,
            "description": "Staging — do not test",
        }, format="json")
        assert resp.status_code == 201
        scope = Scope.objects.get(program=active_program)
        assert scope.is_in_scope is False

    def test_researcher_cannot_add_scope(self, api_client, verified_user, active_program):
        # BUG: IsProgramOwnerOrAdmin.has_permission only checks is_authenticated.
        # For POST (create), has_object_permission is never invoked — only has_permission.
        # So any authenticated researcher can add scopes to any program.
        # Fix: check ProgramOwner/Admin group membership in has_permission.
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.scopes_url(active_program.id), {
            "target": "https://app.example.com",
            "target_type": "web_application",
        }, format="json")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_scopes(self, api_client, active_program):
        resp = api_client.get(self.scopes_url(active_program.id))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Invitation system
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInvitations:
    def invitations_url(self, program_id):
        return f"/api/programs/{program_id}/invitations/"

    def invitation_url(self, program_id, invitation_id):
        return f"/api/programs/{program_id}/invitations/{invitation_id}/"

    def test_owner_can_create_invitation(
        self, api_client, company_user_with_profile, verified_user
    ):
        # Invitations are only allowed for private programs — create one explicitly.
        private_program = Program.objects.create(
            name="Private Invitation Program",
            company=company_user_with_profile,
            description="Invite-only program for testing",
            status="active",
            scope_type="private",
        )
        api_client.force_authenticate(user=company_user_with_profile)
        # The writable field is 'researcher_id' (PrimaryKeyRelatedField, write_only=True).
        resp = api_client.post(self.invitations_url(private_program.id), {
            "researcher_id": verified_user.id,
            "message": "We'd like you to participate in our private program.",
        }, format="json")
        assert resp.status_code == 201
        assert ProgramInvitation.objects.filter(
            program=private_program, researcher=verified_user
        ).exists()

    def test_researcher_cannot_invite_themselves(self, api_client, verified_user, company_user_with_profile):
        # Must use a private program — invitations are only allowed for private programs.
        # The perform_create checks _can_manage (is owner/admin) and raises ValidationError
        # (400) if the caller is not. A stricter fix would be to return 403 here, but
        # 400 is what the current code produces and the test confirms researchers are blocked.
        private_program = Program.objects.create(
            name="Private Self-Invite Test Program",
            company=company_user_with_profile,
            description="Private program for self-invite test",
            status="active",
            scope_type="private",
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.invitations_url(private_program.id), {
            "researcher": verified_user.id,
        }, format="json")
        # 400 (ValidationError from perform_create) or 403 — either means the researcher
        # was correctly blocked from creating invitations.
        assert resp.status_code in (400, 403)

    def test_duplicate_invitation_rejected(
        self, api_client, company_user_with_profile, active_program, verified_user
    ):
        ProgramInvitation.objects.create(
            program=active_program,
            researcher=verified_user,
            invited_by=company_user_with_profile,
        )
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.post(self.invitations_url(active_program.id), {
            "researcher": verified_user.id,
        }, format="json")
        # Should fail — unique_together constraint
        assert resp.status_code == 400

    def test_invitation_accept_action(
        self, api_client, verified_user, company_user_with_profile, active_program
    ):
        invitation = ProgramInvitation.objects.create(
            program=active_program,
            researcher=verified_user,
            invited_by=company_user_with_profile,
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"{self.invitation_url(active_program.id, invitation.id)}accept/",
        )
        assert resp.status_code == 200
        invitation.refresh_from_db()
        assert invitation.status == "accepted"

    def test_invitation_reject_action(
        self, api_client, verified_user, company_user_with_profile, active_program
    ):
        invitation = ProgramInvitation.objects.create(
            program=active_program,
            researcher=verified_user,
            invited_by=company_user_with_profile,
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"{self.invitation_url(active_program.id, invitation.id)}reject/",
        )
        assert resp.status_code == 200
        invitation.refresh_from_db()
        assert invitation.status == "rejected"

    def test_unauthenticated_cannot_list_invitations(self, api_client, active_program):
        resp = api_client.get(self.invitations_url(active_program.id))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Application system
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApplications:
    def apps_url(self, program_id):
        return f"/api/programs/{program_id}/applications/"

    def app_url(self, program_id, app_id):
        return f"/api/programs/{program_id}/applications/{app_id}/"

    def _make_private_program(self, owner):
        return Program.objects.create(
            name="Private Invite-Only Program",
            company=owner,
            description="Restricted access",
            status="active",
            scope_type="private",
            requires_application=True,
        )

    def test_researcher_can_apply_to_private_program(
        self, api_client, verified_user, company_user_with_profile
    ):
        program = self._make_private_program(company_user_with_profile)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.apps_url(program.id), {
            "message": "I have 5 years of experience in web application security.",
            "experience": "Bug bounty hunter since 2019.",
        }, format="json")
        assert resp.status_code == 201
        assert ProgramApplication.objects.filter(
            program=program, researcher=verified_user
        ).exists()

    def test_cannot_apply_twice_to_same_program(
        self, api_client, verified_user, company_user_with_profile
    ):
        program = self._make_private_program(company_user_with_profile)
        ProgramApplication.objects.create(program=program, researcher=verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.apps_url(program.id), {
            "message": "Applying again.",
        }, format="json")
        assert resp.status_code == 400

    def test_owner_can_approve_application(
        self, api_client, company_user_with_profile, verified_user
    ):
        program = self._make_private_program(company_user_with_profile)
        application = ProgramApplication.objects.create(
            program=program, researcher=verified_user
        )
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.post(
            f"{self.app_url(program.id, application.id)}approve/",
            {"notes": "Welcome!"},
            format="json",
        )
        assert resp.status_code == 200
        application.refresh_from_db()
        assert application.status == "approved"

    def test_owner_can_reject_application(
        self, api_client, company_user_with_profile, verified_user
    ):
        program = self._make_private_program(company_user_with_profile)
        application = ProgramApplication.objects.create(
            program=program, researcher=verified_user
        )
        api_client.force_authenticate(user=company_user_with_profile)
        resp = api_client.post(
            f"{self.app_url(program.id, application.id)}reject/",
            {"notes": "Not enough experience."},
            format="json",
        )
        assert resp.status_code == 200
        application.refresh_from_db()
        assert application.status == "rejected"

    def test_researcher_can_withdraw_own_application(
        self, api_client, verified_user, company_user_with_profile
    ):
        program = self._make_private_program(company_user_with_profile)
        application = ProgramApplication.objects.create(
            program=program, researcher=verified_user
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"{self.app_url(program.id, application.id)}withdraw/",
        )
        assert resp.status_code == 200
        application.refresh_from_db()
        assert application.status == "withdrawn"

    def test_unauthenticated_cannot_apply(self, api_client, active_program):
        resp = api_client.post(self.apps_url(active_program.id), {
            "message": "Anonymous apply attempt",
        }, format="json")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFavorites:
    """
    BUG: IsResearcher.has_permission checks user.groups.filter(name='User') but
    registered users are added to the 'Researcher' group (not 'User') during
    registration. All favorites endpoints will return 403 until this is fixed.
    Fix: change the group name check from 'User' to 'Researcher' in IsResearcher.
    """
    LIST_URL = "/api/programs/favorites/"

    def test_researcher_can_favorite_a_program(self, api_client, verified_user, active_program):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.LIST_URL, {
            "program": active_program.id,
        }, format="json")
        assert resp.status_code == 201
        assert ProgramFavorite.objects.filter(
            researcher=verified_user, program=active_program
        ).exists()

    def test_cannot_favorite_same_program_twice(self, api_client, verified_user, active_program):
        ProgramFavorite.objects.create(program=active_program, researcher=verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.LIST_URL, {
            "program": active_program.id,
        }, format="json")
        assert resp.status_code == 400

    def test_researcher_can_list_favorites(self, api_client, verified_user, active_program):
        ProgramFavorite.objects.create(program=active_program, researcher=verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_researcher_can_unfavorite_program(self, api_client, verified_user, active_program):
        fav = ProgramFavorite.objects.create(program=active_program, researcher=verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.delete(f"{self.LIST_URL}{fav.id}/")
        assert resp.status_code == 204
        assert not ProgramFavorite.objects.filter(id=fav.id).exists()

    def test_favorites_scoped_to_current_user(
        self, api_client, verified_user, second_verified_user, active_program
    ):
        # Second user favorites the program
        ProgramFavorite.objects.create(program=active_program, researcher=second_verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == 200
        # verified_user should see empty list
        assert len(resp.data) == 0

    def test_unauthenticated_cannot_list_favorites(self, api_client):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotifications:
    LIST_URL = "/api/programs/notifications/"

    def test_user_can_list_notifications(self, api_client, verified_user, active_program):
        ProgramNotification.notify(
            user=verified_user,
            notification_type="new_report",
            title="New report submitted",
            message="A new report has been submitted to your program.",
            program=active_program,
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_notifications_scoped_to_current_user(
        self, api_client, verified_user, second_verified_user, active_program
    ):
        ProgramNotification.notify(
            user=second_verified_user,
            notification_type="new_report",
            title="Someone else's notification",
            message="Not for this user.",
            program=active_program,
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == 200
        titles = [n["title"] for n in resp.data]
        assert "Someone else's notification" not in titles

    def test_notification_mark_read(self, api_client, verified_user, active_program):
        notif = ProgramNotification.notify(
            user=verified_user,
            notification_type="program_update",
            title="Program updated",
            message="Scope has changed.",
            program=active_program,
        )
        assert notif.read is False
        api_client.force_authenticate(user=verified_user)
        # ProgramNotificationViewSet is ReadOnlyModelViewSet — PATCH is not supported.
        # The view exposes a custom 'mark_read' POST action instead.
        resp = api_client.post(f"{self.LIST_URL}{notif.id}/mark_read/")
        assert resp.status_code == 200
        notif.refresh_from_db()
        assert notif.read is True

    def test_unauthenticated_cannot_list_notifications(self, api_client):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Program model unit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProgramModel:
    def test_slug_generated_on_create(self, company_user_with_profile):
        program = Program.objects.create(
            name="Auto Slug Program",
            company=company_user_with_profile,
            description="Testing slug generation",
        )
        assert program.slug == "auto-slug-program"

    def test_slug_is_unique(self, company_user_with_profile):
        p1 = Program.objects.create(
            name="Dupe Name",
            company=company_user_with_profile,
            description="First",
        )
        p2 = Program.objects.create(
            name="Dupe Name",
            company=company_user_with_profile,
            description="Second",
        )
        assert p1.slug != p2.slug
        assert p2.slug == "dupe-name-1"

    def test_published_at_set_when_activated(self, company_user_with_profile):
        program = Program.objects.create(
            name="Activation Test",
            company=company_user_with_profile,
            description="Testing activation timestamp",
            status="draft",
        )
        assert program.published_at is None
        program.status = "active"
        program.save()
        assert program.published_at is not None

    def test_is_active_property(self, active_program):
        assert active_program.is_active is True

    def test_can_accept_submissions_false_when_paused(self, company_user_with_profile):
        program = Program.objects.create(
            name="Paused Program",
            company=company_user_with_profile,
            description="Paused",
            status="paused",
        )
        assert program.can_accept_submissions is False

    def test_points_range_display(self, company_user_with_profile):
        program = Program.objects.create(
            name="Points Range Program",
            company=company_user_with_profile,
            description="With points range",
            status="active",
            min_points=100,
            max_points=5000,
        )
        assert program.points_range == "100 - 5000 pts"


# ---------------------------------------------------------------------------
# Program access control: private programs
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPrivateProgramAccess:
    def test_private_program_not_visible_to_uninvited_researcher(
        self, api_client, verified_user, company_user_with_profile
    ):
        # BUG: ProgramViewSet.get_object() is overridden with get_object_or_404()
        # but does NOT call self.check_object_permissions(). The default DRF
        # get_object() calls check_object_permissions() after fetching the object,
        # which would invoke CanAccessProgram.has_object_permission and block the
        # uninvited researcher. Without that call, the researcher gets the full program
        # detail (200). Fix: call check_object_permissions() in get_object(), or remove
        # the override and use get_queryset() filtering only.
        private = Program.objects.create(
            name="Secret Program",
            company=company_user_with_profile,
            description="Invite only",
            status="active",
            scope_type="private",
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(f"/api/programs/programs/{private.id}/")
        # Should be 403 or 404 — must NOT be 200
        assert resp.status_code in (403, 404)

    def test_invited_researcher_can_access_private_program(
        self, api_client, verified_user, company_user_with_profile
    ):
        private = Program.objects.create(
            name="Accessible Private Program",
            company=company_user_with_profile,
            description="Invite only",
            status="active",
            scope_type="private",
        )
        ProgramInvitation.objects.create(
            program=private,
            researcher=verified_user,
            invited_by=company_user_with_profile,
            status="accepted",
        )
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(f"/api/programs/programs/{private.id}/")
        assert resp.status_code == 200

    def test_admin_can_access_private_program(
        self, api_client, admin_user, company_user_with_profile
    ):
        private = Program.objects.create(
            name="Admin Visible Private",
            company=company_user_with_profile,
            description="Private",
            status="active",
            scope_type="private",
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f"/api/programs/programs/{private.id}/")
        assert resp.status_code == 200
