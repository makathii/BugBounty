"""
Revoked sessions must really stop working.

Found by the full-program test: "log out of all devices" only flipped a flag in the session list;
the old access token kept working and the old refresh token kept minting new ones. Sessions are now
identified by an id carried in both tokens and checked on every request and every refresh.
"""
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import PasswordResetToken, UserSession

PASSWORD = "SafePass123!"
PROFILE = "/api/users/profile/"
REFRESH = "/api/token/refresh/"


@pytest.fixture
def user(verified_user):
    verified_user.set_password(PASSWORD)
    verified_user.save()
    return verified_user


def login(user):
    response = APIClient().post("/api/token/", {"username": user.username, "password": PASSWORD}, format="json")
    assert response.status_code == 200, response.data
    return response.data["access"], response.data["refresh"]


def get_profile(access):
    return APIClient().get(PROFILE, HTTP_AUTHORIZATION=f"Bearer {access}").status_code


def get_profile_with_cookie(access):
    client = APIClient()
    client.cookies[settings.JWT_AUTH_COOKIE] = access
    return client.get(PROFILE).status_code


def refresh(refresh_token):
    return APIClient().post(REFRESH, {"refresh": refresh_token}, format="json")


def _sid(token):
    from rest_framework_simplejwt.tokens import AccessToken
    return AccessToken(token)["sid"]


@pytest.mark.django_db
class TestSignOutEverywhere:
    def test_old_access_token_stops_working(self, user):
        access, _ = login(user)
        assert get_profile(access) == 200
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert authed.delete("/api/users/sessions/revoke-all/").status_code == 200
        assert get_profile(access) == 401
        assert get_profile_with_cookie(access) == 401

    def test_old_refresh_token_stops_minting_tokens(self, user):
        access, refresh_token = login(user)
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        authed.delete("/api/users/sessions/revoke-all/")
        assert refresh(refresh_token).status_code == 401

    def test_other_users_are_untouched(self, user, second_verified_user):
        second_verified_user.set_password(PASSWORD)
        second_verified_user.save()
        mine, _ = login(user)
        theirs, their_refresh = login(second_verified_user)
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {mine}")
        authed.delete("/api/users/sessions/revoke-all/")
        assert get_profile(theirs) == 200
        assert refresh(their_refresh).status_code == 200


@pytest.mark.django_db
class TestRevokingOneSession:
    def test_only_that_device_is_signed_out(self, user):
        laptop, laptop_refresh = login(user)
        phone, phone_refresh = login(user)
        laptop_session = UserSession.objects.get(jti=_sid(laptop))
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {phone}")
        assert authed.delete(f"/api/users/sessions/{laptop_session.id}/").status_code == 200
        assert get_profile(laptop) == 401
        assert refresh(laptop_refresh).status_code == 401
        assert get_profile(phone) == 200
        assert refresh(phone_refresh).status_code == 200


@pytest.mark.django_db
class TestRefreshKeepsTheSession:
    def test_a_refreshed_token_is_still_the_same_session(self, user):
        access, refresh_token = login(user)
        renewed = refresh(refresh_token)
        assert renewed.status_code == 200
        new_access = renewed.data["access"]
        assert _sid(new_access) == _sid(access)          # same session across rotation
        assert get_profile(new_access) == 200
        assert UserSession.objects.filter(user=user).count() == 1

    def test_revoking_after_a_refresh_still_kills_the_new_tokens(self, user):
        """The original flaw: sessions were keyed by the FIRST access token only."""
        access, refresh_token = login(user)
        renewed = refresh(refresh_token).data
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {renewed['access']}")
        authed.delete("/api/users/sessions/revoke-all/")
        assert get_profile(renewed["access"]) == 401
        assert refresh(renewed["refresh"]).status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_kills_the_access_and_refresh_tokens(self, user):
        access, refresh_token = login(user)
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert authed.post("/api/users/logout/", {"refresh": refresh_token}, format="json").status_code in (200, 204)
        assert get_profile(access) == 401
        assert refresh(refresh_token).status_code == 401

    def test_logout_ends_only_this_session(self, user):
        a, a_refresh = login(user)
        b, b_refresh = login(user)
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {a}")
        authed.post("/api/users/logout/", {"refresh": a_refresh}, format="json")
        assert get_profile(b) == 200


@pytest.mark.django_db
class TestPasswordResetSignsEveryoneOut:
    def test_tokens_issued_before_the_reset_stop_working(self, user):
        access, refresh_token = login(user)
        assert get_profile(access) == 200
        token = PasswordResetToken.create_for_user(user)
        reset = APIClient().post("/api/users/password-reset/confirm/", {
            "token": token.token, "password": "BrandNewPass99!", "password2": "BrandNewPass99!",
        }, format="json")
        assert reset.status_code == 200
        assert get_profile(access) == 401
        assert refresh(refresh_token).status_code == 401
        # ...and the new password logs in normally
        fresh = APIClient().post("/api/token/", {"username": user.username, "password": "BrandNewPass99!"}, format="json")
        assert fresh.status_code == 200 and get_profile(fresh.data["access"]) == 200


@pytest.mark.django_db
class TestLegacyTokens:
    def test_tokens_without_a_session_id_still_work_until_they_expire(self, user):
        legacy = RefreshToken.for_user(user)  # as issued before sessions had ids
        assert "sid" not in legacy.access_token.payload
        assert get_profile(str(legacy.access_token)) == 200
        assert refresh(str(legacy)).status_code == 200

    def test_sign_out_everywhere_also_kills_a_legacy_refresh_token(self, user):
        from users.session_tokens import revoke_all_sessions
        legacy = RefreshToken.for_user(user)
        revoke_all_sessions(user)
        assert refresh(str(legacy)).status_code == 401


@pytest.mark.django_db
def test_every_login_gets_its_own_session_id(user):
    first, _ = login(user)
    second, _ = login(user)
    assert _sid(first) != _sid(second)
    assert UserSession.objects.filter(user=user, is_active=True).count() == 2
