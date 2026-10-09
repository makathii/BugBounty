"""
Tests for session management — list / revoke / revoke-all (Task 5).
"""
import pytest
from django.contrib.auth.models import User
from users.models import UserSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_session(user, device='Test Browser', ip='127.0.0.1'):
    return UserSession.objects.create(
        user=user,
        jti=f'jti-{user.pk}-{device}',
        device_name=device,
        ip_address=ip,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserSessionModel:
    def test_session_created_correctly(self, verified_user):
        s = _create_session(verified_user)
        assert s.is_active is True
        assert s.user == verified_user

    def test_inactive_session_is_not_active(self, verified_user):
        s = _create_session(verified_user)
        s.is_active = False
        s.save()
        assert UserSession.objects.filter(user=verified_user, is_active=True).count() == 0


# ---------------------------------------------------------------------------
# Endpoint: GET /api/users/sessions/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestListSessions:
    URL = '/api/users/sessions/'

    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 401

    def test_returns_only_active_sessions(self, api_client, verified_user):
        _create_session(verified_user, device='ActiveBrowser')
        s2 = _create_session(verified_user, device='InactiveBrowser')
        s2.is_active = False
        s2.save()

        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        names = [s['device_name'] for s in resp.data['sessions']]
        assert 'ActiveBrowser' in names
        assert 'InactiveBrowser' not in names

    def test_returns_only_current_users_sessions(self, api_client, verified_user, second_verified_user):
        _create_session(verified_user)
        _create_session(second_verified_user)

        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        session_ids = [s['id'] for s in resp.data['sessions']]
        other_sessions = UserSession.objects.filter(user=second_verified_user)
        for os in other_sessions:
            assert os.id not in session_ids

    def test_session_fields_present(self, api_client, verified_user):
        _create_session(verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        session = resp.data['sessions'][0]
        assert 'id' in session
        assert 'device_name' in session
        assert 'ip_address' in session
        assert 'created_at' in session
        assert 'last_active' in session


# ---------------------------------------------------------------------------
# Endpoint: DELETE /api/users/sessions/<id>/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRevokeSession:
    def url(self, session_id):
        return f'/api/users/sessions/{session_id}/'

    def test_revoke_own_session(self, api_client, verified_user):
        s = _create_session(verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.delete(self.url(s.id))
        assert resp.status_code == 200
        s.refresh_from_db()
        assert s.is_active is False

    def test_cannot_revoke_another_users_session(self, api_client, verified_user, second_verified_user):
        s = _create_session(second_verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.delete(self.url(s.id))
        assert resp.status_code == 404  # must not leak that the session exists
        s.refresh_from_db()
        assert s.is_active is True  # session untouched

    def test_revoke_nonexistent_session_returns_404(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.delete(self.url(99999))
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.delete('/api/users/sessions/1/')
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Endpoint: DELETE /api/users/sessions/revoke-all/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRevokeAllSessions:
    URL = '/api/users/sessions/revoke-all/'

    def test_revokes_all_active_sessions(self, api_client, verified_user):
        for i in range(3):
            _create_session(verified_user, device=f'Device{i}')
        api_client.force_authenticate(user=verified_user)
        resp = api_client.delete(self.URL)
        assert resp.status_code == 200
        assert UserSession.objects.filter(user=verified_user, is_active=True).count() == 0

    def test_does_not_affect_other_users_sessions(self, api_client, verified_user, second_verified_user):
        _create_session(second_verified_user)
        api_client.force_authenticate(user=verified_user)
        api_client.delete(self.URL)
        assert UserSession.objects.filter(user=second_verified_user, is_active=True).count() == 1

    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.delete(self.URL)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestLoginAndLogoutTrackSessions:
    """Session bookkeeping is best-effort (wrapped in try/except), so a broken
    import there is silent; this pins that login records a session and logout
    deactivates it."""

    def test_login_creates_session_and_logout_deactivates_it(self, api_client, verified_user):
        resp = api_client.post(
            '/api/token/', {'username': verified_user.username, 'password': 'SafePass123!'}, format='json'
        )
        assert resp.status_code == 200
        assert UserSession.objects.filter(user=verified_user, is_active=True).count() == 1

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        out = api_client.post('/api/users/logout/', {'refresh_token': resp.data['refresh']}, format='json')

        assert out.status_code in (200, 205)
        assert UserSession.objects.filter(user=verified_user, is_active=True).count() == 0
