"""
Forced 2FA enrollment for Admin/Triager (they cannot log in without 2FA and
cannot set it up without logging in). See users/mfa_enrollment.py.
"""
import pyotp
import pytest

from users import mfa_enrollment
from users.mfa_enrollment import make_enrollment_token
from users.models import AccountLockout, BackupCode, Profile, UserMFA

LOGIN = '/api/token/'
SETUP = '/api/users/mfa/enroll/setup/'
CONFIRM = '/api/users/mfa/enroll/confirm/'
PASSWORD = 'SafePass123!'


@pytest.fixture
def triager(verified_user, triager_group):
    verified_user.groups.add(triager_group)
    return verified_user


def _login(client, user, **extra):
    return client.post(LOGIN, {'username': user.username, 'password': PASSWORD, **extra}, format='json')


def _token(client, user):
    resp = _login(client, user)
    assert resp.status_code == 400 and resp.data['code'] == 'mfa_enrollment_required'
    return resp.data['enrollment_token']


@pytest.mark.django_db
class TestLoginIssuesEnrollmentToken:
    def test_triager_without_2fa_gets_enrollment_token_and_no_jwts(self, api_client, triager):
        resp = _login(api_client, triager)
        assert resp.status_code == 400
        assert resp.data['code'] == 'mfa_enrollment_required'
        assert resp.data['enrollment_token']
        assert 'access' not in resp.data and 'refresh' not in resp.data
        assert 'two-factor' in resp.data['detail'].lower()

    def test_admin_group_also_enrolls(self, api_client, verified_user, admin_group):
        verified_user.groups.add(admin_group)
        assert _login(api_client, verified_user).data['code'] == 'mfa_enrollment_required'

    def test_disabled_but_existing_mfa_row_also_enrolls(self, api_client, triager):
        UserMFA.objects.create(user=triager, secret=UserMFA.generate_secret(), is_enabled=False)
        assert _login(api_client, triager).data['code'] == 'mfa_enrollment_required'

    def test_wrong_password_gets_no_token(self, api_client, triager):
        resp = api_client.post(LOGIN, {'username': triager.username, 'password': 'nope'}, format='json')
        assert resp.status_code in (400, 401)
        assert 'enrollment_token' not in str(resp.data)

    def test_unverified_email_gets_no_token(self, api_client, triager):
        Profile.objects.filter(user=triager).update(email_verified=False)
        resp = _login(api_client, triager)
        assert resp.status_code == 400
        assert 'enrollment_token' not in str(resp.data)

    def test_locked_account_gets_no_token(self, api_client, triager):
        lockout = AccountLockout.get_or_create_for_user(triager)
        for _ in range(AccountLockout.LOCKOUT_THRESHOLD):
            lockout.record_failure()
        resp = _login(api_client, triager)
        assert 'enrollment_token' not in str(resp.data)
        assert 'locked' in str(resp.data).lower()

    def test_researcher_logs_in_normally(self, api_client, verified_user):
        resp = _login(api_client, verified_user)
        assert resp.status_code == 200 and 'access' in resp.data


@pytest.mark.django_db
class TestEnrollmentFlow:
    def test_full_flow_then_login_with_code(self, api_client, triager):
        token = _token(api_client, triager)

        setup = api_client.post(SETUP, {'enrollment_token': token}, format='json')
        assert setup.status_code == 200
        secret = setup.data['secret']
        assert triager.email in setup.data['provisioning_uri'] or 'otpauth://' in setup.data['provisioning_uri']
        assert not UserMFA.objects.get(user=triager).is_enabled     # not enabled until confirmed

        confirm = api_client.post(
            CONFIRM, {'enrollment_token': token, 'code': pyotp.TOTP(secret).now()}, format='json')
        assert confirm.status_code == 200
        assert len(confirm.data['backup_codes']) == BackupCode.CODES_PER_USER
        assert 'access' not in confirm.data                          # enrollment never mints a session
        assert UserMFA.objects.get(user=triager).is_enabled

        # Now the normal 2FA login works, with a TOTP code...
        assert 'totp_code' in _login(api_client, triager).data
        ok = _login(api_client, triager, totp_code=pyotp.TOTP(secret).now())
        assert ok.status_code == 200 and 'access' in ok.data
        # ...or a backup code.
        ok2 = _login(api_client, triager, totp_code=confirm.data['backup_codes'][0])
        assert ok2.status_code == 200

    def test_wrong_code_does_not_enable(self, api_client, triager):
        token = _token(api_client, triager)
        api_client.post(SETUP, {'enrollment_token': token}, format='json')
        resp = api_client.post(CONFIRM, {'enrollment_token': token, 'code': '000000'}, format='json')
        assert resp.status_code == 400
        assert not UserMFA.objects.get(user=triager).is_enabled

    def test_confirm_before_setup_rejected(self, api_client, triager):
        token = _token(api_client, triager)
        resp = api_client.post(CONFIRM, {'enrollment_token': token, 'code': '123456'}, format='json')
        assert resp.status_code == 400

    def test_confirm_requires_code(self, api_client, triager):
        token = _token(api_client, triager)
        api_client.post(SETUP, {'enrollment_token': token}, format='json')
        assert api_client.post(CONFIRM, {'enrollment_token': token}, format='json').status_code == 400

    def test_token_stops_working_once_2fa_enabled(self, api_client, triager):
        token = _token(api_client, triager)
        secret = api_client.post(SETUP, {'enrollment_token': token}, format='json').data['secret']
        api_client.post(CONFIRM, {'enrollment_token': token, 'code': pyotp.TOTP(secret).now()}, format='json')
        # Replaying the token must not hand out a new secret for an enrolled account.
        assert api_client.post(SETUP, {'enrollment_token': token}, format='json').status_code == 400
        assert UserMFA.objects.get(user=triager).secret == secret


@pytest.mark.django_db
class TestEnrollmentTokenSecurity:
    @pytest.mark.parametrize('payload', [{}, {'enrollment_token': ''}, {'enrollment_token': 'garbage'}])
    def test_missing_or_garbage_token_rejected(self, api_client, payload):
        assert api_client.post(SETUP, payload, format='json').status_code == 400
        assert api_client.post(CONFIRM, {**payload, 'code': '123456'}, format='json').status_code == 400

    def test_tampered_token_rejected(self, api_client, triager):
        token = _token(api_client, triager)
        assert api_client.post(SETUP, {'enrollment_token': token[:-2] + 'xx'}, format='json').status_code == 400

    def test_expired_token_rejected(self, api_client, triager, monkeypatch):
        token = _token(api_client, triager)
        monkeypatch.setattr(mfa_enrollment, 'ENROLLMENT_MAX_AGE', -1)
        resp = api_client.post(SETUP, {'enrollment_token': token}, format='json')
        assert resp.status_code == 400 and 'expired' in resp.data['detail']

    def test_password_change_revokes_token(self, api_client, triager):
        token = _token(api_client, triager)
        triager.set_password('AnotherPass456!')
        triager.save()
        assert api_client.post(SETUP, {'enrollment_token': token}, format='json').status_code == 400

    def test_token_for_non_required_role_rejected(self, api_client, verified_user):
        # Researchers have optional 2FA and must use the authenticated endpoints.
        token = make_enrollment_token(verified_user)
        assert api_client.post(SETUP, {'enrollment_token': token}, format='json').status_code == 400

    def test_enrollment_token_is_not_an_api_credential(self, api_client, triager):
        token = _token(api_client, triager)
        resp = api_client.get('/api/users/mfa/status/', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert resp.status_code == 401

    def test_enrollment_endpoints_are_throttled(self):
        from users import views
        from users.throttles import MfaEnrollThrottle
        assert MfaEnrollThrottle.scope == 'mfa_enroll'
        for fn in (views.mfa_enroll_setup, views.mfa_enroll_confirm):
            assert MfaEnrollThrottle in fn.cls.throttle_classes
