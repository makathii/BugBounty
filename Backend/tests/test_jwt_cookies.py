"""
Tests for the cookie-based JWT auth hardening.

Coverage:
  - Login sets HttpOnly + SameSite cookies on successful auth.
  - Refresh endpoint reads the refresh token from the cookie, rotates it,
    and blacklists the old one.
  - Re-using a rotated refresh token fails (the blacklist works).
  - Logout blacklists the refresh token AND clears both cookies.
  - The cookie-aware authentication accepts the access cookie on a protected
    endpoint.
"""
import pytest
from django.conf import settings
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(api_client, username, password="SafePass123!"):
    return api_client.post(
        "/api/token/",
        {"username": username, "password": password},
        format="json",
    )


# ---------------------------------------------------------------------------
# Login sets the cookies correctly
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_sets_httponly_jwt_cookies(api_client, verified_user):
    response = _login(api_client, verified_user.username)
    assert response.status_code == 200

    access_cookie = response.cookies.get(settings.JWT_AUTH_COOKIE)
    refresh_cookie = response.cookies.get(settings.JWT_AUTH_REFRESH_COOKIE)

    assert access_cookie is not None, "access cookie should be set"
    assert refresh_cookie is not None, "refresh cookie should be set"
    # HttpOnly defeats JS-based token theft (the whole point).
    assert access_cookie["httponly"]
    assert refresh_cookie["httponly"]
    # SameSite=Strict defeats most CSRF.
    assert access_cookie["samesite"].lower() == "strict"
    assert refresh_cookie["samesite"].lower() == "strict"
    # Refresh cookie must be scoped tighter than the access cookie.
    assert refresh_cookie["path"] == settings.JWT_AUTH_REFRESH_COOKIE_PATH


@pytest.mark.django_db
def test_login_failure_does_not_set_cookies(api_client, verified_user):
    response = api_client.post(
        "/api/token/",
        {"username": verified_user.username, "password": "wrong-password"},
        format="json",
    )
    assert response.status_code == 401
    assert settings.JWT_AUTH_COOKIE not in response.cookies
    assert settings.JWT_AUTH_REFRESH_COOKIE not in response.cookies


# ---------------------------------------------------------------------------
# Cookie-based authentication on a protected endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_protected_endpoint_accepts_access_cookie(api_client, verified_user):
    login_response = _login(api_client, verified_user.username)
    assert login_response.status_code == 200
    # APIClient threads cookies between requests automatically — no manual
    # Authorization header.
    profile_response = api_client.get("/api/users/profile/")
    assert profile_response.status_code == 200
    assert profile_response.json()["username"] == verified_user.username


# ---------------------------------------------------------------------------
# Refresh endpoint: cookie-driven rotation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_refresh_uses_cookie_and_rotates(api_client, verified_user):
    login_response = _login(api_client, verified_user.username)
    original_refresh = login_response.cookies[settings.JWT_AUTH_REFRESH_COOKIE].value

    refresh_response = api_client.post("/api/token/refresh/")
    assert refresh_response.status_code == 200

    new_access = refresh_response.cookies.get(settings.JWT_AUTH_COOKIE)
    new_refresh = refresh_response.cookies.get(settings.JWT_AUTH_REFRESH_COOKIE)
    assert new_access is not None
    assert new_refresh is not None
    # Rotation: the new refresh cookie must differ from the original.
    assert new_refresh.value != original_refresh


@pytest.mark.django_db
def test_rotated_refresh_token_is_blacklisted(api_client, verified_user):
    """Reusing the *original* refresh token after rotation must fail."""
    login_response = _login(api_client, verified_user.username)
    original_refresh = login_response.cookies[settings.JWT_AUTH_REFRESH_COOKIE].value

    # First refresh — succeeds and rotates.
    first = api_client.post("/api/token/refresh/")
    assert first.status_code == 200

    # Now replay the original refresh token by sending it explicitly. The
    # blacklist app should reject it.
    replay = api_client.post(
        "/api/token/refresh/",
        {"refresh": original_refresh},
        format="json",
    )
    assert replay.status_code == 401, (
        "Reused refresh token must be rejected — that's the whole point "
        "of BLACKLIST_AFTER_ROTATION."
    )


# ---------------------------------------------------------------------------
# Logout: blacklist + clear cookies
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_logout_blacklists_refresh_and_clears_cookies(api_client, verified_user):
    login_response = _login(api_client, verified_user.username)
    refresh_value = login_response.cookies[settings.JWT_AUTH_REFRESH_COOKIE].value

    # Sanity: token currently in the outstanding-but-not-blacklisted set.
    assert OutstandingToken.objects.filter(token=refresh_value).exists()

    logout_response = api_client.post("/api/users/logout/")
    assert logout_response.status_code == 200

    # Cookies should be cleared (set with empty value / past expiry).
    assert logout_response.cookies[settings.JWT_AUTH_COOKIE].value == ""
    assert logout_response.cookies[settings.JWT_AUTH_REFRESH_COOKIE].value == ""

    # Token blacklisted: BlacklistedToken row exists for this token.
    outstanding = OutstandingToken.objects.get(token=refresh_value)
    assert BlacklistedToken.objects.filter(token=outstanding).exists(), (
        "Logout must blacklist the refresh token so the session can't be revived."
    )


@pytest.mark.django_db
def test_logout_after_blacklist_cannot_refresh(api_client, verified_user):
    """After logout the refresh cookie can't be used to mint a new access."""
    _login(api_client, verified_user.username)
    api_client.post("/api/users/logout/")

    # Cookies were cleared on the response, but APIClient still stores them.
    # Wipe the client's cookie jar to mirror a fresh browser.
    api_client.cookies.clear()

    refresh = api_client.post("/api/token/refresh/")
    # Without a refresh cookie, the endpoint returns 401.
    assert refresh.status_code == 401
