"""
Tests for user profile, groups, and CSRF endpoints.

These endpoints existed with no prior test coverage:
  - GET/PATCH /api/users/profile/
  - GET /api/users/groups/
  - GET /api/users/csrf/
"""
import pytest
from django.contrib.auth.models import User


# ---------------------------------------------------------------------------
# Profile endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserProfile:
    URL = "/api/users/profile/"

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_authenticated_user_can_retrieve_profile(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["username"] == verified_user.username
        assert resp.data["email"] == verified_user.email

    def test_password_not_in_profile_response(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert "password" not in resp.data

    def test_user_can_update_own_profile(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(
            self.URL,
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
        )
        assert resp.status_code == 200
        verified_user.refresh_from_db()
        assert verified_user.first_name == "Updated"
        assert verified_user.last_name == "Name"

    def test_user_can_update_email(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(
            self.URL,
            {"email": "newemail@example.com"},
            format="json",
        )
        assert resp.status_code == 200
        verified_user.refresh_from_db()
        assert verified_user.email == "newemail@example.com"

    def test_profile_returns_correct_username(self, api_client, verified_user, second_verified_user):
        """Each user sees their own profile, not another user's."""
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.data["username"] == verified_user.username
        assert resp.data["username"] != second_verified_user.username


# ---------------------------------------------------------------------------
# Groups endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserGroups:
    URL = "/api/users/groups/"

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_researcher_group_reflected(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["is_researcher"] is True
        assert resp.data["is_admin"] is False

    def test_triager_group_reflected(self, api_client, triager_user):
        api_client.force_authenticate(user=triager_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["is_triager"] is True
        assert resp.data["is_researcher"] is False

    def test_admin_group_reflected(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["is_admin"] is True

    def test_company_group_reflected(self, api_client, company_user):
        api_client.force_authenticate(user=company_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["is_company"] is True
        assert resp.data["is_program_owner"] is True

    def test_groups_list_present(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert "groups" in resp.data
        assert isinstance(resp.data["groups"], list)
        assert "Researcher" in resp.data["groups"]


# ---------------------------------------------------------------------------
# CSRF token endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCSRFEndpoint:
    URL = "/api/users/csrf/"

    def test_csrf_endpoint_returns_200_unauthenticated(self, api_client):
        """Must be AllowAny — needed before login."""
        resp = api_client.get(self.URL)
        assert resp.status_code == 200

    def test_csrf_response_contains_token(self, api_client):
        resp = api_client.get(self.URL)
        assert "csrfToken" in resp.data
        assert resp.data["csrfToken"]  # non-empty

    def test_csrf_sets_cookie(self, client):
        """Django test client respects CSRF cookie setting."""
        resp = client.get(self.URL)
        assert resp.status_code == 200
        # The csrftoken cookie should be set so JS can read it
        assert "csrftoken" in resp.cookies
