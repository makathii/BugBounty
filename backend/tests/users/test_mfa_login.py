"""
Login for accounts with 2FA enabled: password step -> challenge token -> code step.
(Forced enrollment for Admin/Triager is covered in test_mfa_enrollment.py.)
"""
import pyotp
import pytest

from users import mfa_challenge
from users.mfa_challenge import make_challenge_token
from users.models import AccountLockout, BackupCode, UserMFA, UserSession

LOGIN = '/api/token/'
PASSWORD = 'SafePass123!'


@pytest.fixture
def mfa_user(verified_user):
    """A plain researcher who opted into 2FA (not a required-2FA role)."""
    UserMFA.objects.create(user=verified_user, secret=UserMFA.generate_secret(), is_enabled=True)
    return verified_user


def _password_step(client, user):
    resp = client.post(LOGIN, {'username': user.username, 'password': PASSWORD}, format='json')
    assert resp.status_code == 400 and resp.data['code'] == 'mfa_required', resp.data
    return resp.data['mfa_token']


def _totp(user):
    return pyotp.TOTP(user.mfa.secret).now()


@pytest.mark.django_db
class TestPasswordStep:
    def test_optional_2fa_is_enforced_at_login(self, api_client, mfa_user):
        resp = api_client.post(LOGIN, {'username': mfa_user.username, 'password': PASSWORD}, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'mfa_required' and resp.data['mfa_token']
        assert 'access' not in resp.data and 'refresh' not in resp.data
        assert 'totp_code' in resp.data           # legacy shape for older API clients

    def test_user_without_2fa_logs_in_directly(self, api_client, verified_user):
        resp = api_client.post(LOGIN, {'username': verified_user.username, 'password': PASSWORD}, format='json')
        assert resp.status_code == 200 and 'access' in resp.data

    def test_disabled_2fa_row_does_not_challenge(self, api_client, verified_user):
        UserMFA.objects.create(user=verified_user, secret=UserMFA.generate_secret(), is_enabled=False)
        assert api_client.post(LOGIN, {'username': verified_user.username, 'password': PASSWORD},
                               format='json').status_code == 200

    def test_wrong_password_gets_no_challenge_token(self, api_client, mfa_user):
        resp = api_client.post(LOGIN, {'username': mfa_user.username, 'password': 'nope'}, format='json')
        assert resp.status_code in (400, 401) and 'mfa_token' not in str(resp.data)

    def test_one_shot_login_with_code_still_works(self, api_client, mfa_user):
        resp = api_client.post(
            LOGIN, {'username': mfa_user.username, 'password': PASSWORD, 'totp_code': _totp(mfa_user)},
            format='json')
        assert resp.status_code == 200 and 'access' in resp.data


@pytest.mark.django_db
class TestCodeStep:
    def test_valid_totp_completes_login_and_records_session(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        resp = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': _totp(mfa_user)}, format='json')
        assert resp.status_code == 200
        assert resp.data['access'] and resp.data['refresh']
        assert UserSession.objects.filter(user=mfa_user, is_active=True).count() == 1
        # the new access token really authenticates
        me = api_client.get('/api/users/profile/', HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        assert me.status_code == 200 and me.data['username'] == mfa_user.username

    def test_backup_code_works_once(self, api_client, mfa_user):
        codes = BackupCode.generate_for_user(mfa_user)
        token = _password_step(api_client, mfa_user)
        ok = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': codes[0]}, format='json')
        assert ok.status_code == 200
        again = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': codes[0]}, format='json')
        assert again.status_code == 400

    def test_wrong_code_rejected_without_tokens(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        resp = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': '000000'}, format='json')
        assert resp.status_code == 400 and 'totp_code' in resp.data
        assert 'access' not in resp.data

    def test_missing_code_rejected(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        resp = api_client.post(LOGIN, {'mfa_token': token}, format='json')
        assert resp.status_code == 400 and 'access' not in resp.data

    def test_guessing_codes_locks_the_account(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        for _ in range(AccountLockout.LOCKOUT_THRESHOLD):
            api_client.post(LOGIN, {'mfa_token': token, 'totp_code': '000000'}, format='json')
        # even the correct code is refused while locked
        resp = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': _totp(mfa_user)}, format='json')
        assert resp.status_code == 400 and 'locked' in str(resp.data).lower()
        assert 'access' not in resp.data


@pytest.mark.django_db
class TestChallengeTokenSecurity:
    @pytest.mark.parametrize('token', ['', 'garbage'])
    def test_bad_token_rejected(self, api_client, mfa_user, token):
        resp = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': _totp(mfa_user)}, format='json')
        assert resp.status_code == 400 and 'access' not in resp.data

    def test_tampered_token_rejected(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        resp = api_client.post(LOGIN, {'mfa_token': token[:-2] + 'xx', 'totp_code': _totp(mfa_user)}, format='json')
        assert resp.status_code == 400 and resp.data['code'] == 'mfa_token_expired'

    def test_expired_token_rejected(self, api_client, mfa_user, monkeypatch):
        token = _password_step(api_client, mfa_user)
        monkeypatch.setattr(mfa_challenge, 'CHALLENGE_MAX_AGE', -1)
        resp = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': _totp(mfa_user)}, format='json')
        assert resp.status_code == 400 and resp.data['code'] == 'mfa_token_expired'

    def test_password_change_revokes_token(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        mfa_user.set_password('AnotherPass456!')
        mfa_user.save()
        resp = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': _totp(mfa_user)}, format='json')
        assert resp.status_code == 400 and 'access' not in resp.data

    def test_token_useless_if_2fa_was_disabled_meanwhile(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        UserMFA.objects.filter(user=mfa_user).update(is_enabled=False)
        # No code needed any more? No: the token alone must NOT log anyone in.
        resp = api_client.post(LOGIN, {'mfa_token': token}, format='json')
        assert resp.status_code == 400 and 'access' not in resp.data
        resp2 = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': '123456'}, format='json')
        assert resp2.status_code == 400 and 'access' not in resp2.data

    def test_unverified_email_blocks_challenge_completion(self, api_client, mfa_user):
        from users.models import Profile
        token = make_challenge_token(mfa_user)
        Profile.objects.filter(user=mfa_user).update(email_verified=False)
        resp = api_client.post(LOGIN, {'mfa_token': token, 'totp_code': _totp(mfa_user)}, format='json')
        assert resp.status_code == 400 and 'access' not in resp.data

    def test_challenge_token_is_not_an_api_credential(self, api_client, mfa_user):
        token = _password_step(api_client, mfa_user)
        assert api_client.get('/api/users/profile/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code == 401

    def test_missing_username_and_password_without_token_rejected(self, api_client):
        assert api_client.post(LOGIN, {}, format='json').status_code == 400
