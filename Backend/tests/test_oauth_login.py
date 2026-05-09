"""
Tests for the OAuth client-login flow.

We stub out the actual HTTP calls to the providers so the tests don't hit
the network. Three things matter security-wise and are exercised here:

  1. State-parameter CSRF protection on the callback.
  2. Misconfigured provider returns 503, not 500.
  3. A successful callback creates / links a User + SocialAccount and
     issues HttpOnly JWT cookies.
"""
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User

from users.models import SocialAccount


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def github_configured(settings):
    settings.OAUTH_PROVIDERS = {
        **settings.OAUTH_PROVIDERS,
        "github": {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scope": "read:user user:email",
        },
    }
    return settings


@pytest.fixture
def github_unconfigured(settings):
    settings.OAUTH_PROVIDERS = {
        **settings.OAUTH_PROVIDERS,
        "github": {"client_id": "", "client_secret": "", "scope": ""},
    }
    return settings


@pytest.fixture(autouse=True)
def researcher(db):
    Group.objects.get_or_create(name="Researcher")


# ---------------------------------------------------------------------------
# /start/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_oauth_start_returns_authorize_url_and_state_cookie(api_client, github_configured):
    response = api_client.get("/api/users/oauth/github/start/")
    assert response.status_code == 200

    body = response.json()
    assert "authorize_url" in body
    assert body["authorize_url"].startswith("https://github.com/login/oauth/authorize?")
    assert "state=" in body["authorize_url"]
    assert "client_id=test-client-id" in body["authorize_url"]

    # State cookie present and HttpOnly (we don't want JS reading it).
    state = response.cookies.get("bb_oauth_state")
    assert state is not None
    assert state["httponly"]


@pytest.mark.django_db
def test_oauth_start_unknown_provider_404s(api_client):
    response = api_client.get("/api/users/oauth/myspace/start/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_oauth_start_unconfigured_provider_503s(api_client, github_unconfigured):
    response = api_client.get("/api/users/oauth/github/start/")
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# /callback/ — security checks
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_callback_rejects_missing_state(api_client, github_configured):
    response = api_client.get("/api/users/oauth/github/callback/?code=abc")
    assert response.status_code == 400


@pytest.mark.django_db
def test_callback_rejects_state_mismatch(api_client, github_configured):
    """State parameter must match the value stored in the cookie."""
    start = api_client.get("/api/users/oauth/github/start/")
    assert start.status_code == 200
    # Real state is in the cookie; pass a different one in the URL.
    response = api_client.get(
        "/api/users/oauth/github/callback/?code=abc&state=tampered-value"
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# /callback/ — happy path with mocked provider
# ---------------------------------------------------------------------------

def _mock_token_response(token="prov-access-token"):
    class _Resp:
        status_code = 200
        def json(self): return {"access_token": token, "token_type": "bearer"}
    return _Resp()


def _mock_userinfo_response(payload):
    class _Resp:
        status_code = 200
        def json(self): return payload
    return _Resp()


@pytest.mark.django_db
def test_callback_creates_user_and_sets_jwt_cookies(api_client, github_configured):
    # Step 1 — start, which sets the state cookie.
    start = api_client.get("/api/users/oauth/github/start/")
    state_cookie = api_client.cookies["bb_oauth_state"].value

    # Step 2 — mock the network calls the callback would make:
    #   POST token_url   -> token_response
    #   GET  userinfo_url -> userinfo_response
    github_userinfo = {
        "id": 4242,
        "login": "octouser",
        "email": "octouser@example.com",
    }

    def fake_post(url, *args, **kwargs):
        return _mock_token_response()

    def fake_get(url, *args, **kwargs):
        if "api.github.com/user" in url and "/emails" not in url:
            return _mock_userinfo_response(github_userinfo)
        if "/user/emails" in url:
            class R:
                status_code = 200
                def json(self):
                    return [{"email": "octouser@example.com",
                             "primary": True, "verified": True}]
            return R()
        raise AssertionError(f"Unexpected GET to {url}")

    with patch("users.oauth_providers.requests.post", side_effect=fake_post), \
         patch("users.oauth_providers.requests.get", side_effect=fake_get):
        response = api_client.get(
            f"/api/users/oauth/github/callback/?code=auth-code-xyz&state={state_cookie}",
            follow=False,
        )

    # Step 3 — the callback redirects (302) back to the frontend, with our
    # JWT cookies attached to the redirect response.
    assert response.status_code in (301, 302)
    assert settings.JWT_AUTH_COOKIE in response.cookies
    assert settings.JWT_AUTH_REFRESH_COOKIE in response.cookies
    assert response.cookies[settings.JWT_AUTH_COOKIE]["httponly"]

    # Step 4 — User + SocialAccount were created and linked.
    user = User.objects.get(email="octouser@example.com")
    assert user.profile.email_verified, (
        "Provider asserted email_verified, so we should mark our profile verified."
    )
    assert SocialAccount.objects.filter(
        user=user, provider="github", provider_uid="4242"
    ).exists()
    assert user.groups.filter(name="Researcher").exists()


@pytest.mark.django_db
def test_callback_links_existing_user_by_verified_email(
    api_client, github_configured, verified_user
):
    """If a verified-email match already exists, link rather than dupe."""
    start = api_client.get("/api/users/oauth/github/start/")
    state_cookie = api_client.cookies["bb_oauth_state"].value

    # Provider asserts the same email AND email_verified=True — safe to link.
    github_userinfo = {
        "id": 9999,
        "login": "newhandle",
        "email": verified_user.email,
    }

    def fake_post(url, *a, **kw):
        return _mock_token_response()

    def fake_get(url, *a, **kw):
        if "api.github.com/user" in url and "/emails" not in url:
            return _mock_userinfo_response(github_userinfo)
        class R:
            status_code = 200
            def json(self):
                return [{"email": verified_user.email,
                         "primary": True, "verified": True}]
        return R()

    user_count_before = User.objects.count()
    with patch("users.oauth_providers.requests.post", side_effect=fake_post), \
         patch("users.oauth_providers.requests.get", side_effect=fake_get):
        response = api_client.get(
            f"/api/users/oauth/github/callback/?code=abc&state={state_cookie}",
            follow=False,
        )
    assert response.status_code in (301, 302)

    # No new user — existing one was linked.
    assert User.objects.count() == user_count_before
    assert SocialAccount.objects.filter(
        user=verified_user, provider="github", provider_uid="9999"
    ).exists()
